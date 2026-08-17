"""Tests for EventSequenceDetector class.

This module tests the EventSequenceDetector implementation including:
- Initialization and configuration
- Training functionality to learn known EventID sequences
- Detection logic for unknown sequences
- Window handling (reset_window) and end-to-end regression on audit.log
"""

import pytest
from pydantic import ValidationError

from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetector, \
    EventSequenceDetectorConfig, BufferMode
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas
from detectmatelibrary.common.detector import PersistConfig
from detectmatelibrary.common._core_op._fit_logic import EnumState
from detectmatelibrary.utils.aux import time_test_mode
from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "event_sequence_detector",
            "auto_config": False,
            "params": {
                "fixed_window_size": 2
            }
        },
        "MultipleDetector": {
            "method_type": "event_sequence_detector",
            "auto_config": False,
            "params": {
                "fixed_window_size": 2
            }
        }
    }
}


def _make_schema(event_id, template="test template", log_id="1"):
    return schemas.ParserSchema({
        "parserType": "test",
        "EventID": event_id,
        "template": template,
        "variables": ["adsasd", "asdasd"],
        "logID": log_id,
        "parsedLogID": log_id,
        "parserID": "test_parser",
        "log": "test log message",
        "logFormatVariables": {"level": "INFO"}
    })


class TestEventSequenceDetectorInitialization:
    """Test EventSequenceDetector initialization and configuration."""

    def test_default_initialization(self):
        detector = EventSequenceDetector()

        assert detector.name == "EventSequenceDetector"
        assert hasattr(detector, "config")
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema
        assert hasattr(detector, "persistency")
        # unconfigured until auto-config picks a length
        assert detector.config.fixed_window_size is None
        assert (detector.config.min_window_size, detector.config.max_window_size) == (2, 10)

    def test_custom_config_initialization(self):
        detector = EventSequenceDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert detector.config.fixed_window_size == 2
        assert hasattr(detector, "persistency")
        assert isinstance(detector.persistency.events_data, dict)


class TestEventSequenceDetectorTraining:
    """Test EventSequenceDetector training functionality."""

    def test_train_learns_sequence(self):
        detector = EventSequenceDetector(config=config, name="MultipleDetector")

        for event_id in [1, 2, 3]:
            detector.train(_make_schema(event_id))

        # fixed_window_size=2 -> sequences (1, 2) and (2, 3) are learned
        assert detector.get_known_sequences() == {(1, 2), (2, 3)}

    def test_train_below_window_length_learns_nothing(self):
        detector = EventSequenceDetector(config=config, name="MultipleDetector")

        # Only one event seen so far, window not yet full (fixed_window_size=2)
        detector.train(_make_schema(1))

        assert detector.get_known_sequences() == set()


class TestEventSequenceDetectorDetection:
    """Test EventSequenceDetector detection functionality."""

    def test_detect_known_sequence_no_alert(self):
        detector = EventSequenceDetector(config=config, name="MultipleDetector")

        # Repeating the cycle 1 -> 2 -> 3 teaches sequences (1,2), (2,3), (3,1)
        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_make_schema(event_id))
        # The detection window is independent of the training one, so prime it
        # with a 3 before appending the 1 that completes the known (3, 1)
        detector.detect(_make_schema(3, log_id="6"), schemas.DetectorSchema())
        output = schemas.DetectorSchema()
        result = detector.detect(_make_schema(1, log_id="7"), output)

        assert not result
        assert output.score == 0.0

    def test_detect_unknown_sequence_alert(self):
        detector = EventSequenceDetector(config=config, name="MultipleDetector")

        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_make_schema(event_id))

        # (3, 9) was never seen during training
        detector.detect(_make_schema(3, log_id="6"), schemas.DetectorSchema())
        output = schemas.DetectorSchema()
        result = detector.detect(_make_schema(9, log_id="7"), output)

        assert result
        assert output.score == 1.0
        assert any("Sequence" in key for key in output["alertsObtain"])

    def test_detect_below_window_length_no_alert(self):
        detector = EventSequenceDetector(config=config, name="MultipleDetector")

        # First event with an empty detector: window not yet full, can't be an anomaly
        output = schemas.DetectorSchema()
        result = detector.detect(_make_schema(1), output)

        assert not result
        assert output.score == 0.0


class TestEventSequenceDetectorWindow:
    """Test sliding-window behaviour."""

    def test_reset_window_clears_state(self):
        detector = EventSequenceDetector(config=config, name="MultipleDetector")

        detector.train(_make_schema(1))
        detector.detect(_make_schema(1), schemas.DetectorSchema())
        assert len(detector._train_window) == 1
        assert len(detector._detect_window) == 1

        detector.reset_window()
        assert len(detector._train_window) == 0
        assert len(detector._detect_window) == 0

    def test_train_and_detect_windows_are_independent(self):
        """CoreComponent.process() calls train() and detect() for the same
        event, so a shared window would ingest every training event twice."""
        detector = EventSequenceDetector(
            name="Independent",
            config=EventSequenceDetectorConfig(auto_config=False, fixed_window_size=3,
                                               data_use_training=6),
        )

        alerts = [
            detector.process(_make_schema(event_id, log_id=str(i)))
            for i, event_id in enumerate([1, 2, 3, 1, 2, 3])
        ]

        assert detector.get_known_sequences() == {(1, 2, 3), (2, 3, 1), (3, 1, 2)}
        assert all(alert is None for alert in alerts)


_PARSER_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>:*): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": AUDIT_TEMPLATES,
            },
        }
    }
}


class TestEventSequenceDetectorEndToEnd:
    """Regression test: full train/detect pipeline on audit.log."""

    def test_audit_log_anomalies(self):
        pars = MatcherParser(config=_PARSER_CONFIG)
        detector = EventSequenceDetector(
            config=EventSequenceDetectorConfig(auto_config=False, fixed_window_size=3),
            name="EventSequenceDetector",
        )

        logs = list(From.log(pars, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        # One novel event, reported once per window it appears in: with
        # fixed_window_size=3 that is three consecutive log IDs.
        assert detected_ids == {"1863", "1864", "1865"}

    def test_audit_log_anomalies_via_process(self):
        """Same regression, driven through process() so the configure ->
        set_configuration -> train -> detect lifecycle is exercised."""
        pars = MatcherParser(config=_PARSER_CONFIG)
        detector = EventSequenceDetector(name="EventSequenceProcess")

        logs = list(From.log(pars, in_path=AUDIT_LOG, do_process=True))

        # Phase 1: configure
        detector.fitlogic.config_state.current = EnumState.KEEP
        for log in logs[:TRAIN_UNTIL]:
            detector.process(log)

        # Transition: next process() call triggers set_configuration()
        detector.fitlogic.config_state.current = EnumState.STOP

        # Phase 2: train
        detector.fitlogic.train_state.current = EnumState.KEEP
        for log in logs[:TRAIN_UNTIL]:
            detector.process(log)

        # auto-config settles on the longest stable window in [2..10]
        assert detector.config.fixed_window_size == 7

        # Phase 3: detect only
        detector.fitlogic.train_state.current = EnumState.STOP
        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            if detector.process(log) is not None:
                detected_ids.add(log["logID"])

        # The novel event at 1863 plus the neighbouring windows it invalidates:
        # a 7-long window makes more sequences unique than a short one.
        assert detected_ids == {str(log_id) for log_id in range(1861, 1871)}


# A repeating event yields a constant window sequence at every length, so the
# stability tracker classifies it STATIC — the cycle 1 -> 2 -> 3 changes on every
# step and is stable at no length at all.
_STABLE_STREAM = [1] * 8


class TestEventSequenceDetectorAutoConfig:
    """Test the auto-configuration of fixed_window_size."""

    def test_short_configure_phase_skips_unfilled_candidates(self):
        """Candidates whose window never filled produce no tracker data and
        must be skipped rather than looked up: 6 configure events cannot fill a
        window of 7 or 8."""
        detector = EventSequenceDetector(
            name="ShortConfig",
            config=EventSequenceDetectorConfig(
                data_use_configure=6, data_use_training=1,
                min_window_size=2, max_window_size=8,
            ),
        )

        for i, event_id in enumerate(_STABLE_STREAM):
            detector.process(_make_schema(event_id, log_id=str(i)))

        assert detector.config.fixed_window_size == 4

    def test_set_configuration_preserves_user_config(self):
        """Auto-configuration must only change fixed_window_size."""
        detector = EventSequenceDetector(
            name="Preserve",
            config=EventSequenceDetectorConfig(
                parser="MySequenceParser",
                data_use_configure=6,
                data_use_training=10,
                use_config_data_as_training=False,
                min_window_size=2,
                max_window_size=8,
            ),
        )

        for i, event_id in enumerate(_STABLE_STREAM):
            detector.process(_make_schema(event_id, log_id=str(i)))

        assert detector.config.fixed_window_size is not None
        assert detector.config.parser == "MySequenceParser"
        assert detector.config.data_use_training == 10
        assert detector.config.use_config_data_as_training is False
        assert (detector.config.min_window_size, detector.config.max_window_size) == (2, 8)

    def test_configure_windows_follow_config_changes(self):
        """_configure_windows is built lazily, so changing the range after
        construction must not raise."""
        detector = EventSequenceDetector(
            name="LateCandidates",
            config=EventSequenceDetectorConfig(min_window_size=2, max_window_size=3),
        )
        detector.config.min_window_size = 4
        detector.config.max_window_size = 5

        detector.configure(_make_schema(1))

        assert set(detector._configure_windows) == {4, 5}

    def test_fixed_window_size_skips_auto_config(self):
        """A user-set fixed_window_size wins over the candidate range."""
        detector = EventSequenceDetector(
            name="FixedWins",
            config=EventSequenceDetectorConfig(
                data_use_configure=5, data_use_training=1,
                min_window_size=4, max_window_size=6, fixed_window_size=2,
            ),
        )

        for i, event_id in enumerate([1, 2, 3, 1, 2, 3]):
            detector.process(_make_schema(event_id, log_id=str(i)))

        assert detector.config.fixed_window_size == 2
        assert detector._configure_windows == {}

    def test_no_stable_window_size_generates_no_instance(self):
        """No stable candidate must leave the detector unconfigured rather than
        fall back to an arbitrary length that alerts on everything."""
        detector = EventSequenceDetector(
            name="NoStable",
            config=EventSequenceDetectorConfig(
                data_use_configure=5, data_use_training=1,
                # no window of 8+ can fill within a 5-event configure phase
                min_window_size=8, max_window_size=10,
            ),
        )

        for i, event_id in enumerate([1, 2, 3, 1, 2, 3]):
            detector.process(_make_schema(event_id, log_id=str(i)))

        assert detector.config.fixed_window_size is None

        # unconfigured: neither learns nor alerts
        for event_id in [4, 5, 6, 7]:
            detector.train(_make_schema(event_id))
        assert detector.get_known_sequences() == set()
        assert not detector.detect(_make_schema(9), schemas.DetectorSchema())

    def test_unstable_stream_generates_no_instance(self):
        """The other route to 'no stable candidate': every window fills and
        clears min_samples, but the sequences never settle."""
        detector = EventSequenceDetector(
            name="Unstable",
            config=EventSequenceDetectorConfig(min_window_size=2, max_window_size=4),
        )

        for i, event_id in enumerate(range(30)):  # every event ID unique
            detector.configure(_make_schema(event_id, log_id=str(i)))

        # all three candidates produced enough samples to be classified, so the
        # verdict below comes from classify() and not from a starved window
        trackers = [
            tracker.get_data()["seq"]
            for tracker in detector.auto_conf_persistency.get_events_data().values()
        ]
        assert len(trackers) == 3
        assert all(len(t.change_series) >= t.min_samples for t in trackers)

        detector.set_configuration()

        assert detector.config.fixed_window_size is None
        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_make_schema(event_id))
        assert detector.get_known_sequences() == set()
        assert not detector.detect(_make_schema(9), schemas.DetectorSchema())

    def test_auto_config_off_without_fixed_window_size_is_inert(self):
        detector = EventSequenceDetector(
            name="NoWindow",
            config=EventSequenceDetectorConfig(auto_config=False),
        )

        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_make_schema(event_id))

        assert detector.get_known_sequences() == set()
        assert not detector.detect(_make_schema(9), schemas.DetectorSchema())


_CYCLE_3_GRAMS = {(1, 2, 3), (2, 3, 1), (3, 1, 2)}


def _save_trained_detector(name, path, fixed_window_size=3):
    """Train the 1 -> 2 -> 3 cycle and persist the resulting model."""
    detector = EventSequenceDetector(
        name=name,
        config=EventSequenceDetectorConfig(
            auto_config=False,
            fixed_window_size=fixed_window_size,
            persist=PersistConfig(path=path),
        ),
    )
    for event_id in [1, 2, 3, 1, 2, 3]:
        detector.train(_make_schema(event_id))
    assert detector.saver is not None
    detector.saver.save()
    detector.saver.stop()
    return detector


class TestEventSequenceDetectorPersist:
    """Sequences are stored as fixed-length n-grams, so a restored model is
    only valid at the length it was trained with."""

    def test_no_saver_by_default(self):
        assert EventSequenceDetector().saver is None

    def test_saver_created_when_persist_configured(self):
        detector = EventSequenceDetector(
            name="NSD_Saver",
            config=EventSequenceDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path="memory://nsd_saver/state"),
            ),
        )
        assert detector.saver is not None
        detector.saver.stop()

    def test_reload_at_matching_length_restores_model(self):
        base_path = "memory://nsd_match/state"
        _save_trained_detector("NSD_Match", base_path, fixed_window_size=3)

        det2 = EventSequenceDetector(
            name="NSD_Match",
            config=EventSequenceDetectorConfig(
                auto_config=False,
                fixed_window_size=3,
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert det2.saver is not None
        det2.saver.stop()

        assert det2.config.fixed_window_size == 3
        assert det2.get_known_sequences() == _CYCLE_3_GRAMS

    def test_reload_adopts_persisted_sequence_length(self):
        base_path = "memory://nsd_reload/state"
        _save_trained_detector("NSD_Reload", base_path, fixed_window_size=3)

        det2 = EventSequenceDetector(
            name="NSD_Reload",
            config=EventSequenceDetectorConfig(
                auto_config=False,
                fixed_window_size=4,  # mismatch: restored model is 3-grams
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert det2.saver is not None
        det2.saver.stop()

        assert det2.config.fixed_window_size == 3
        assert det2.get_known_sequences() == _CYCLE_3_GRAMS

        # the known cycle must not alert under the restored model
        alerted = [
            det2.detect(_make_schema(event_id), schemas.DetectorSchema())
            for event_id in [1, 2, 3, 1, 2, 3]
        ]
        assert not any(alerted)

    def test_import_state_adopts_persisted_sequence_length(self):
        """import_state() runs after __init__, so it has to redo the length
        check that auto_load gets for free."""
        base_path = "memory://nsd_import/state"
        det1 = _save_trained_detector("NSD_Import", base_path, fixed_window_size=3)
        det1.export_state(base_path)

        det2 = EventSequenceDetector(
            name="NSD_Import",
            config=EventSequenceDetectorConfig(auto_config=False, fixed_window_size=4),
        )
        det2.import_state(base_path)

        assert det2.config.fixed_window_size == 3
        assert det2.get_known_sequences() == _CYCLE_3_GRAMS
        assert det2._detect_window.maxlen == 3

    def test_restored_state_disables_auto_config(self):
        """Auto-configuration would pick a length the restored sequences were
        never encoded at."""
        base_path = "memory://nsd_autoconf/state"
        _save_trained_detector("NSD_AutoConf", base_path, fixed_window_size=3)

        det2 = EventSequenceDetector(
            name="NSD_AutoConf",
            config=EventSequenceDetectorConfig(
                data_use_configure=5,
                data_use_training=1,
                min_window_size=4, max_window_size=5,  # 3 deliberately excluded
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert det2.saver is not None
        det2.saver.stop()

        for i, event_id in enumerate([1, 2, 3, 1, 2, 3]):
            det2.process(_make_schema(event_id, log_id=str(i)))

        assert det2.config.fixed_window_size == 3
        assert _CYCLE_3_GRAMS <= det2.get_known_sequences()

    def test_persist_survives_empty_configuration(self):
        """The no-instance path replaces the whole config object, so the
        persist block has to be carried over by hand."""
        base_path = "memory://nsd_nostable/state"
        detector = EventSequenceDetector(
            name="NSD_NoStable",
            config=EventSequenceDetectorConfig(
                data_use_configure=5,
                data_use_training=1,
                # no window of 8+ can fill within a 5-event configure phase
                min_window_size=8,
                max_window_size=10,
                persist=PersistConfig(path=base_path),
            ),
        )
        assert detector.saver is not None

        for i, event_id in enumerate([1, 2, 3, 1, 2, 3]):
            detector.process(_make_schema(event_id, log_id=str(i)))
        detector.saver.stop()

        assert detector.config.fixed_window_size is None
        assert detector.config.persist is not None
        assert detector.config.persist.path == base_path

    def test_training_continues_after_reload(self):
        base_path = "memory://nsd_continue/state"
        _save_trained_detector("NSD_Continue", base_path, fixed_window_size=3)

        det2 = EventSequenceDetector(
            name="NSD_Continue",
            config=EventSequenceDetectorConfig(
                auto_config=False,
                fixed_window_size=3,
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert det2.saver is not None
        det2.saver.stop()

        for event_id in [7, 8, 9]:
            det2.train(_make_schema(event_id))

        # restored sequences survive and the new one joins them at the same length
        assert det2.get_known_sequences() == _CYCLE_3_GRAMS | {(7, 8, 9)}


class TestEventSequenceDetectorConfigValidation:
    """Window lengths below 1 disable detection silently, so reject them."""

    def test_zero_fixed_window_size_rejected(self):
        with pytest.raises(ValidationError):
            EventSequenceDetectorConfig(fixed_window_size=0)

    def test_zero_min_window_size_rejected(self):
        with pytest.raises(ValidationError):
            EventSequenceDetectorConfig(min_window_size=0)

    def test_inverted_window_range_rejected(self):
        with pytest.raises(ValidationError):
            EventSequenceDetectorConfig(min_window_size=5, max_window_size=4)

    def test_removed_fields_rejected(self):
        """Extra='forbid': configs written for the old field names must fail
        loudly rather than silently run with defaults."""
        with pytest.raises(ValidationError):
            EventSequenceDetectorConfig(max_sequence_length=3)
