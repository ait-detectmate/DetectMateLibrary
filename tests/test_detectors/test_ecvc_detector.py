
from detectmatelibrary.detectors.ecvc_detector import ECVCOp, ECVCDetectorConfig, ECVCDetector
from detectmatelibrary.base_detectors import SequenceAutoConfigParams
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.utils.persistency.data_structures.trackers import ClassificationMethods
from detectmatelibrary.utils.sequence_encoding import decode_count_vec
from detectmatelibrary import schemas

from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

import copy
import logging

import numpy as np
import pytest
from pydantic import ValidationError


def _event(event_id, log_id="1", header=None):
    return schemas.ParserSchema({
        "eventID": event_id, "template": "t", "logID": log_id, "headerVariables": header or {},
    })


class TestECVCOP:
    def test_build_count_vec(self):
        input_ = [
            schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]
        ]
        expected = tuple([2, 1, 0, 0, 1])

        assert ECVCOp.build_count_vec(input_) == expected

    def test_build_one_vec(self):
        input_ = [
            schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]
        ]

        expected = np.array([2, 1, 0, 0, 1, 0, 0, 0])
        assert np.array_equal(ECVCOp.build_one_vec(input_, 8), expected)

        expected = np.array([2, 1, 0, 0, 1])
        assert np.array_equal(ECVCOp.build_one_vec(input_, 3), expected)

    def test_init_count_matrix(self):
        input_ = [
            (1, 0, 2, 1), (1, 2, 1), (0, 1, 4)
        ]
        expected = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])

        assert np.array_equal(ECVCOp.init_count_matrix(input_), expected)

    def test_calculate_score(self):
        input_ = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])
        y = np.array([0, 1, 4, 0, 0])

        assert 0.0 == ECVCOp.calculate_score(y, matrix=input_)

        input_ = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])
        y = np.array([0, 1, 4, 0])

        assert 0.0 == ECVCOp.calculate_score(y, matrix=input_)

    def test_calculate_threshol(self):
        matrix = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])
        y = np.array([[1, 1, 1, 1], [0, 0, 0, 1]])

        assert 0.0 == ECVCOp.threshold_cal(y, matrix=matrix, method="default")
        assert 0.575 == ECVCOp.threshold_cal(y, matrix=matrix, method="mean")


class TestECVC:
    def test_window_size(self):
        # get_window_size() reports the core buffer (1 under NO_BUF), not the ECVC windows.
        ecvc = ECVCDetector(config=ECVCDetectorConfig(fixed_window_size=7))
        assert ecvc.config.fixed_window_size == 7
        assert ecvc._train_window.maxlen == 7
        assert ecvc._detect_window.maxlen == 7

    def test_ecvc(self):
        config = {
            "detectors": {
                "ECVCDetector": {
                    "method_type": "ecvc_detector",
                    "fixed_window_size": 3,
                    "seed": 0,
                    "validation_per": 0.,
                    "threshold_method": "mean",
                    "data_use_training": 30,
                }
            }
        }

        ecvc = ECVCDetector(config=config)

        input_ = []
        for _ in range(10):
            input_.extend([schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]])

        for in_ in input_:
            ecvc.process(in_)
        assert ecvc.get_state() == "Default"

        for in_ in input_[5:15]:
            alert = ecvc.process(in_)
        assert alert is None

        for in_ in [schemas.ParserSchema({"eventID": i}) for i in [4, 4, 4, 4, 4, 4, 1, 0, 1, 1]]:
            alert = ecvc.process(in_)
        assert alert is not None

    def test_legacy_method_type_still_loads(self):
        config = {
            "detectors": {"ECVCDetector": {"method_type": "ecvc_detector_detector", "fixed_window_size": 3}}
        }

        with pytest.warns(DeprecationWarning, match="ecvc_detector_detector"):
            ecvc = ECVCDetector(config=config)

        assert ecvc.config.method_type == "ecvc_detector"
        assert ecvc.config.fixed_window_size == 3
        assert "ecvc_detector_detector" in str(config)  # caller's dict is left untouched

    @pytest.mark.parametrize("entry", [{"window_size": 3}, {"params": {"window_size": 3}}])
    def test_legacy_window_size_still_loads(self, entry):
        config = {"detectors": {"ECVCDetector": {"method_type": "ecvc_detector", **entry}}}
        original = copy.deepcopy(config)

        with pytest.warns(DeprecationWarning, match="window_size"):
            ecvc = ECVCDetector(config=config)

        assert ecvc.config.fixed_window_size == 3
        assert config == original  # caller's dict is left untouched

    def test_window_size_and_fixed_window_size_together_rejected(self):
        config = {"detectors": {"ECVCDetector": {
            "method_type": "ecvc_detector", "window_size": 3, "fixed_window_size": 4,
        }}}

        with pytest.raises(ValueError, match="Both 'window_size' and 'fixed_window_size' are set"):
            ECVCDetectorConfig.from_dict(config, "ECVCDetector")

    def test_alert_lists_every_log_in_the_window(self):
        ecvc = ECVCDetector(config=ECVCDetectorConfig(
            fixed_window_size=3, data_use_training=9, validation_per=0.,
        ))

        for log_id, event_id in enumerate([0, 1, 2] * 3):
            ecvc.process(_event(event_id, log_id=str(log_id)))
        for log_id in ["9", "10", "11"]:
            alert = ecvc.process(_event(5, log_id=log_id))

        assert alert is not None
        assert list(alert["logIDs"]) == ["9", "10", "11"]
        assert len(alert["logTimestamps"]) == 3

    def test_empty_validation_split_warns(self, caplog):
        ecvc = ECVCDetector(config=ECVCDetectorConfig(fixed_window_size=3))
        for _ in range(5):
            ecvc.train(_event(1))

        with caplog.at_level(logging.WARNING):
            ecvc.post_train()
            ecvc._sync_from_state()  # a later sync (restore, aggregate) does not repeat it

        assert sum("validation split is empty" in r.message for r in caplog.records) == 1
        assert ecvc.threshold == 0.0

    def test_training_that_never_fills_a_window_warns(self, caplog):
        """Three training logs cannot fill a window of five, so nothing is
        learned and the detector never alerts; say so instead of staying
        silent."""
        ecvc = ECVCDetector(config=ECVCDetectorConfig(fixed_window_size=5, data_use_training=3))

        with caplog.at_level(logging.WARNING):
            _process_all(ecvc, [1, 2, 3, 1, 2])  # the 4th record ends training

        assert ecvc.count_vecs is None
        assert sum("no count vectors were learned" in r.message for r in caplog.records) == 1

    @pytest.mark.filterwarnings("ignore:'window_size' is deprecated:DeprecationWarning")
    def test_legacy_window_size_longer_than_training_warns(self, caplog):
        """Five training logs cannot fill a window of ten.

        The old ECVC counted data_use_training in windows, so it always
        learned something; it now counts logs.
        """
        ecvc = ECVCDetector(config={"detectors": {"ECVCDetector": {
            "method_type": "ecvc_detector", "auto_config": False,
            "params": {"window_size": 10, "data_use_training": 5},
        }}})

        with caplog.at_level(logging.WARNING):
            _process_all(ecvc, [1, 2, 3, 1, 2, 3])

        assert ecvc.count_vecs is None
        assert any("no count vectors were learned" in r.message for r in caplog.records)

    def test_auto_config_off_without_size_warns_at_build_and_is_inert(self, caplog):
        with caplog.at_level(logging.WARNING):
            ecvc = ECVCDetector(config=ECVCDetectorConfig(auto_config=False))
        assert any("no fixed_window_size was given" in r.message for r in caplog.records)

        for event_id in [1, 2, 3, 1, 2, 3]:
            ecvc.train(_event(event_id))

        assert ecvc.persistency.get_events_seen() == set()
        assert ecvc.detect(_event(1), schemas.DetectorSchema()) is False

    def test_default_build_does_not_warn(self, caplog):
        with caplog.at_level(logging.WARNING):
            ECVCDetector()
        assert not any("data_use_configure is not set" in r.message for r in caplog.records)

    def test_no_configure_phase_warns_once(self, caplog):
        ecvc = ECVCDetector()
        with caplog.at_level(logging.WARNING):
            for event_id in [1, 2, 3]:
                ecvc.train(_event(event_id))
            ecvc.detect(_event(4), schemas.DetectorSchema())
        assert sum("data_use_configure is not set" in r.message for r in caplog.records) == 1
        assert ecvc.persistency.get_events_seen() == set()


PIPELINE_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": AUDIT_TEMPLATES,
            },
        }
    },
    "detectors": {
        "ECVCDetector": {
            "method_type": "ecvc_detector",
            "fixed_window_size": 10,
            "seed": 0,
            "validation_per": 0.,
            "threshold_method": "mean",
            "data_use_training": TRAIN_UNTIL,
        },
        "ECVCDetector_fed": {
            "method_type": "ecvc_detector_detector",
            "fixed_window_size": 10,
            "allow_fed": True,
            "seed": 0,
            "validation_per": 0.,
            "threshold_method": "mean",
            "data_use_training": TRAIN_UNTIL,
        }
    }
}


class TestECVCDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.ignored
    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector = ECVCDetector(config=PIPELINE_CONFIG)

        detected_ids = set()
        for parsed_log in From.log(parser, in_path=AUDIT_LOG, do_process=True):
            alert = detector.process(parsed_log)
            if detector.get_state() == "Default" and alert is not None:
                detected_ids.update(set([log_id for log_id in alert["logIDs"]]))

        for log_id in {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}:
            assert log_id in detected_ids

    @pytest.mark.ignored
    def test_audit_log_anomalies_to_binary(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector1 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)
        detector2 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs:
            detector1.process(log)

        thress = detector1.threshold
        binary = detector1.to_binary()
        detector2 = detector2.from_binary(binary)

        assert detector2.persistency == detector1.persistency
        assert (detector2.count_vecs == detector1.count_vecs).all()
        assert detector2.threshold == thress

    @pytest.mark.ignored
    def test_audit_log_anomalie_fed(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector1 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)
        detector2 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs:
            detector1.process(log)

        thress = detector1.threshold
        (detector1 + detector2).aggregate()

        assert detector2.persistency == detector1.persistency
        assert (detector2.count_vecs == detector1.count_vecs).all()
        assert detector2.threshold == thress


def _fed_detector(n):
    return ECVCDetector(config=ECVCDetectorConfig(auto_config=False, fixed_window_size=n, allow_fed=True))


def _train_per_line(detector, event_ids):
    for event_id in event_ids:
        detector.train(_event(event_id))
    return detector


class TestECVCDetectorRestoredState:
    """State that arrives after construction sets the window size it was
    trained at and rebuilds the count vectors."""

    def test_from_binary_adopts_the_persisted_window_size(self, tmp_path, monkeypatch, caplog):
        monkeypatch.chdir(tmp_path)  # the slow store writes .temp/ CSVs here
        trained = _train_per_line(_fed_detector(3), [0, 1, 4])

        with caplog.at_level(logging.WARNING):
            restored = _fed_detector(4).from_binary(trained.to_binary())

        assert restored.config.fixed_window_size == 3
        assert restored._detect_window.maxlen == 3
        assert restored.count_vecs is not None
        assert any("window size 3" in r.message for r in caplog.records)

    def test_aggregate_adopts_the_persisted_window_size(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        trained = _train_per_line(_fed_detector(3), [0, 1, 4])
        receiver = _fed_detector(4)

        (receiver + trained).aggregate()

        assert receiver.config.fixed_window_size == 3
        assert receiver._detect_window.maxlen == 3
        assert receiver.count_vecs is not None

    @pytest.mark.parametrize("receiver_size", [4, None])
    def test_stack_then_aggregate_resizes_the_receiver_windows(self, tmp_path, monkeypatch, receiver_size):
        # stack() restores the bytes into a component that shares the receiver's config, so
        # the receiver's config already holds the persisted size when aggregate() syncs it.
        monkeypatch.chdir(tmp_path)
        trained = _train_per_line(_fed_detector(3), [0, 1, 4])
        receiver = ECVCDetector(config=ECVCDetectorConfig(fixed_window_size=receiver_size, allow_fed=True))

        receiver.stack(trained.to_binary())
        receiver.aggregate()

        assert receiver.config.fixed_window_size == 3
        assert receiver._detect_window.maxlen == 3
        assert receiver._train_window.maxlen == 3

    def test_aggregate_over_mixed_window_sizes_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        trained = _train_per_line(_fed_detector(3), [0, 1, 4])
        receiver = _train_per_line(_fed_detector(4), [0, 1, 4, 1])

        with pytest.raises(ValueError, match=r"window sizes \{3: 1, 4: 1\}"):
            (receiver + trained).aggregate()

    def test_finalize_federation_removes_the_slow_table(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        detector = _train_per_line(_fed_detector(3), [0, 1, 4])
        assert (tmp_path / ".temp").exists()

        detector.finalize_federation()

        assert not (tmp_path / ".temp").exists()


# A repeating event gives the same count vector at every window size, so the
# stability tracker classifies every candidate STATIC.
_STABLE_STREAM = [1] * 8


def _process_all(detector, event_ids):
    for i, event_id in enumerate(event_ids):
        detector.process(_event(event_id, log_id=str(i)))
    return detector


def _learned_sizes(detector):
    """The window size of every learned count vector."""
    return {decode_count_vec(str(key))[0] for key in detector.persistency.get_events_seen()}


def _short_configure_detector():
    return ECVCDetector(config=ECVCDetectorConfig(
        data_use_configure=6, data_use_training=1,
        auto_config_params=SequenceAutoConfigParams(min_window_size=2, max_window_size=8),
    ))


class TestECVCDetectorAutoConfig:
    """Test the auto-configuration of fixed_window_size."""

    def test_short_configure_phase_skips_unfilled_candidates(self):
        """Candidates whose window never filled produce no tracker data and
        must be skipped rather than looked up: 6 configure records cannot fill
        a window of 7 or 8."""
        detector = _process_all(_short_configure_detector(), _STABLE_STREAM)

        assert detector.config.fixed_window_size == 4

    def test_replay_trains_at_the_chosen_size(self):
        """The configure records replayed through train() are counted at the
        chosen size."""
        detector = _process_all(_short_configure_detector(), _STABLE_STREAM)

        assert _learned_sizes(detector) == {4}
        assert detector.count_vecs is not None

    def test_phase_boundaries_count_records(self, monkeypatch):
        """Per-line windows: configuring ends after data_use_configure records
        and training after data_use_training more."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            data_use_configure=6, data_use_training=4,
            auto_config_params=SequenceAutoConfigParams(min_window_size=2, max_window_size=3),
        ))
        calls = {"configure": 0, "train": 0}
        for name in calls:
            def counted(input_, _name=name, _method=getattr(detector, name)):
                calls[_name] += 1
                return _method(input_)
            monkeypatch.setattr(detector, name, counted)

        _process_all(detector, [1] * 12)

        assert detector.config.fixed_window_size == 3
        assert calls == {"configure": 6, "train": 10}  # train: 6 replayed + 4
        assert detector.count_vecs is not None

    def test_fixed_window_size_skips_auto_config(self, caplog):
        """A user-set fixed_window_size wins over the candidate range."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            data_use_configure=5, data_use_training=1,
            auto_config_params=SequenceAutoConfigParams(min_window_size=4, max_window_size=6),
            fixed_window_size=2,
        ))

        with caplog.at_level(logging.WARNING):
            _process_all(detector, [1, 2, 3, 1, 2, 3])

        assert detector.config.fixed_window_size == 2
        assert detector._configure_windows == {}
        assert any("fixed_window_size is set" in r.message for r in caplog.records)

    def test_no_stable_window_size_stays_inert(self, caplog):
        """No stable candidate must leave the detector unconfigured rather than
        fall back to an arbitrary size that alerts on everything."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            data_use_configure=5, data_use_training=1,
            # no window of 8+ can fill within a 5-record configure phase
            auto_config_params=SequenceAutoConfigParams(min_window_size=8, max_window_size=10),
        ))

        with caplog.at_level(logging.WARNING):
            _process_all(detector, [1, 2, 3, 1, 2, 3, 1])  # the 7th record ends training

        assert any("no stable window size" in r.message for r in caplog.records)
        # one warning for one cause: no size, so the empty training is not reported again
        assert not any("no count vectors were learned" in r.message for r in caplog.records)
        assert detector.config.fixed_window_size is None

        # unconfigured: neither learns nor alerts
        for event_id in [4, 5, 6, 7]:
            detector.train(_event(event_id))
        assert detector.persistency.get_events_seen() == set()
        assert detector.detect(_event(9), schemas.DetectorSchema()) is False

    def test_unstable_stream_generates_no_instance(self):
        """The other route to 'no stable candidate': every window fills and
        clears min_samples, but the count vectors never settle."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            auto_config_params=SequenceAutoConfigParams(min_window_size=2, max_window_size=4),
        ))

        for i, event_id in enumerate(range(30)):  # every event ID unique
            detector.configure(_event(event_id, log_id=str(i)))

        # all three candidates produced enough samples to be classified, so the
        # verdict below comes from classify() and not from a starved window
        trackers = [
            tracker.get_data()["cvec"]
            for tracker in detector.auto_conf_persistency.get_events_data().values()
        ]
        assert len(trackers) == 3
        assert all(len(t.change_series) >= t.min_samples for t in trackers)

        detector.set_configuration()

        assert detector.config.fixed_window_size is None
        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_event(event_id))
        assert detector.persistency.get_events_seen() == set()
        assert detector.detect(_event(9), schemas.DetectorSchema()) is False

    def test_auto_config_off_stays_inert_through_a_configure_phase(self):
        """A configure phase alone must not pick a size: auto_config=False
        means the configure phase configures nothing."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            auto_config=False, data_use_configure=6, data_use_training=1,
            auto_config_params=SequenceAutoConfigParams(min_window_size=2, max_window_size=8),
        ))

        _process_all(detector, _STABLE_STREAM)

        assert detector.config.fixed_window_size is None
        assert detector._configure_windows == {}
        assert detector.persistency.get_events_seen() == set()

    def test_shared_config_resizes_the_other_detectors_windows(self):
        """Detectors built from one config instance share fixed_window_size.

        The first one's auto-configuration writes its choice into the
        shared config after the others built their windows unbounded, so
        their windows must follow the config rather than grow without
        limit.
        """
        config = ECVCDetectorConfig(
            data_use_configure=6, data_use_training=1,
            auto_config_params=SequenceAutoConfigParams(min_window_size=2, max_window_size=8),
        )
        first = ECVCDetector(config=config)
        trainer = ECVCDetector(config=config)
        scorer = ECVCDetector(config=config)

        _process_all(first, _STABLE_STREAM)
        assert config.fixed_window_size == 4

        for event_id in [1, 2, 3, 1, 2, 3]:
            trainer.train(_event(event_id))
        scorer.detect(_event(1), schemas.DetectorSchema())

        assert trainer._train_window.maxlen == trainer._detect_window.maxlen == 4
        assert scorer._train_window.maxlen == scorer._detect_window.maxlen == 4
        learned = [decode_count_vec(str(key)) for key in trainer.persistency.get_events_seen()]
        assert learned
        assert all(size == 4 and sum(counts) == 4 for size, counts in learned)

    def test_configure_windows_follow_config_changes(self):
        """_configure_windows is built lazily, so changing the range after
        construction must not raise."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            auto_config_params=SequenceAutoConfigParams(min_window_size=2, max_window_size=3),
        ))
        detector.config.auto_config_params.min_window_size = 4
        detector.config.auto_config_params.max_window_size = 5

        detector.configure(_event(1))

        assert set(detector._configure_windows) == {4, 5}

    def test_saved_selected_config_replays(self, caplog):
        """The config dumped after auto-configuration (what the harness's
        --save-config writes) reloads at the chosen size with auto_config off,
        and trains without an inert warning."""
        detector = _process_all(_short_configure_detector(), _STABLE_STREAM)
        dumped = detector.config.to_dict(method_id="ECVCDetector")

        with caplog.at_level(logging.WARNING):
            reloaded = ECVCDetector(config=dumped)
            assert reloaded.config.fixed_window_size == 4
            assert reloaded.config.auto_config is False

            for _ in range(5):
                reloaded.train(_event(1))

        assert _learned_sizes(reloaded) == {4}
        inert_warnings = ("data_use_configure is not set", "no fixed_window_size was given")
        assert not any(w in r.message for r in caplog.records for w in inert_warnings)

    def test_configure_without_training_phase_warns(self, caplog):
        """post_train() runs only after a training phase, so a configure phase
        alone never builds the count vectors detection scores against."""
        with caplog.at_level(logging.WARNING):
            ECVCDetector(config=ECVCDetectorConfig(data_use_configure=5))
        assert any("data_use_training is not set" in r.message for r in caplog.records)

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            ECVCDetector()
        assert not any("data_use_training is not set" in r.message for r in caplog.records)


class TestECVCDetectorConfigValidation:
    """Window sizes below 1 disable detection silently, so reject them."""

    def test_zero_fixed_window_size_rejected(self):
        with pytest.raises(ValidationError):
            ECVCDetectorConfig(fixed_window_size=0)

    def test_window_size_rejected_by_the_constructor(self):
        """The legacy window_size alias is mapped in from_dict only."""
        with pytest.raises(ValidationError):
            ECVCDetectorConfig(window_size=3)

    def test_auto_config_params_round_trip(self):
        block = {"min_window_size": 3, "max_window_size": 7}
        source = {
            "detectors": {
                "ECVCDetector": {
                    "method_type": "ecvc_detector",
                    "auto_config": True,
                    "auto_config_params": block,
                    # Explicit so the first from_dict already coerces `events` to
                    # EventsConfig; see the ESD round-trip test.
                    "events": {},
                }
            }
        }
        config = ECVCDetectorConfig.from_dict(source, "ECVCDetector")
        dumped = config.to_dict(method_id="ECVCDetector")
        entry = dumped["detectors"]["ECVCDetector"]
        assert block.items() <= entry["auto_config_params"].items()
        assert not set(block) & set(entry.get("params", {}))
        assert ECVCDetectorConfig.from_dict(dumped, "ECVCDetector") == config


# A cycle of four events: at every window size new count vectors appear only
# while the first cycle runs, and at size 4 every window holds each event once
# (STATIC). Sizes 2, 3 and 5 are stable under the default segment thresholds and
# unstable under tight ones, which makes the configured classification visible.
_CYCLIC_STREAM = [1, 2, 3, 4] * 5


class TestECVCDetectorClassification:
    """The configure phase runs under the classification the operator asked
    for, and on the time axis when a time method is enabled."""

    @staticmethod
    def _select_window(classification=None):
        params = {"min_window_size": 2, "max_window_size": 5}
        if classification is not None:
            params["classification"] = classification
        detector = ECVCDetector(config=ECVCDetectorConfig(
            data_use_configure=len(_CYCLIC_STREAM) - 1,
            data_use_training=1,
            auto_config_params=SequenceAutoConfigParams(**params),
        ))
        _process_all(detector, _CYCLIC_STREAM)
        return detector.config.fixed_window_size

    def test_classification_decides_the_selected_window(self):
        """One stream, two rules: the default thresholds leave every candidate
        stable and take the longest; tight ones leave only the STATIC size."""
        assert self._select_window() == 5
        assert self._select_window(
            ClassificationMethods(segment_thresholds=[0.01, 0.01, 0.01, 0.01])
        ) == 4

    def test_configure_records_timestamps_for_a_time_method(self):
        """A time-axis method needs per-record timestamps; without them the
        classifier silently falls back to the index axis."""
        detector = ECVCDetector(config=ECVCDetectorConfig(
            auto_config_params=SequenceAutoConfigParams(
                min_window_size=2,
                max_window_size=2,
                classification=ClassificationMethods(index=False, time=True),
                timestamp_variable="ts",
            ),
        ))

        for i, event_id in enumerate(_CYCLIC_STREAM):
            detector.configure(_event(event_id, log_id=str(i), header={"ts": str(1700000000 + i * 60)}))

        tracker = detector.auto_conf_persistency.get_events_data()[2].get_data()["cvec"]
        assert tracker.classification.enabled == ("time",)
        assert len(tracker.timestamps) == len(tracker.change_series)
        assert tracker.timestamps[1] - tracker.timestamps[0] == 60.0

    def test_classification_block_reaches_trackers_from_a_config_dict(self):
        """The benchmark harness configures from YAML, so the block has to
        arrive through from_dict, not only through the constructor."""
        source = {
            "detectors": {
                "ECVCDetector": {
                    "method_type": "ecvc_detector",
                    "auto_config": True,
                    "auto_config_params": {
                        "min_window_size": 2,
                        "max_window_size": 2,
                        "classification": {
                            "index": True,
                            "time": True,
                            "slope_index": True,
                            "decision": "majority",
                        },
                        "timestamp_variable": "ts",
                    },
                }
            }
        }
        detector = ECVCDetector(config=source)

        for i, event_id in enumerate(_CYCLIC_STREAM):
            detector.configure(_event(event_id, log_id=str(i), header={"ts": str(1700000000 + i * 60)}))

        tracker = detector.auto_conf_persistency.get_events_data()[2].get_data()["cvec"]
        assert tracker.classification.enabled == ("index", "time", "slope_index")
        assert tracker.classification.decision == "majority"
        assert len(tracker.timestamps) == len(tracker.change_series)
