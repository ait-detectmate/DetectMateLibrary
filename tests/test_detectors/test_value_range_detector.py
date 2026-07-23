"""Tests for ValueRangeDetector class.

This module tests the ValueRangeDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Event-specific configuration handling
- Input/output schema validation
"""
import logging
import random
import pytest
from detectmatelibrary.common._core_op._fit_logic import TrainState
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetector, ValueRangeDetectorConfig
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.common._core_op._fit_logic import ConfigState
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas
from detectmatelibrary.utils.aux import time_test_mode
from detectmatelibrary.tools.logging import logger
from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL
# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "value_range_detector",
            "auto_config": False,
            "params": {"ignore_non_numerical_val": False},
            "events": {
                1: {
                    "instance1": {
                        "params": {},
                        "variables": [{
                            "pos": 1, "name": "test", "params": {}
                        }]
                    }
                }
            }
        },
        "MultipleDetector": {
            "method_type": "value_range_detector",
            "auto_config": False,
            "params": {"ignore_non_numerical_val": True},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 1, "name": "test", "params": {}
                        }]
                    }
                }
            }
        }
    }
}


class TestValueRangeDetectorInitialization:
    """Test ValueRangeDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = ValueRangeDetector()

        assert detector.name == "ValueRangeDetector"
        assert hasattr(detector, 'config')
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema
        assert hasattr(detector, 'persistency')

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        detector = ValueRangeDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert hasattr(detector, 'persistency')
        assert isinstance(detector.persistency.events_data, dict)

    def test_add_value_updates_tracker(self):
        """add_value (now a method) applies range semantics to a tracker."""
        detector = ValueRangeDetector()
        tracker = SingleStabilityTracker()

        detector.add_value(tracker, "5")   # first value -> change
        detector.add_value(tracker, "7")   # within/extends range
        detector.add_value(tracker, "nope")  # non-numeric -> ignored

        assert tracker.unique_set == {5, 7}
        assert list(tracker.change_series) == [True, True]

    def test_add_value_stores_only_min_max(self):
        """unique_set stays bounded to {min, max} regardless of how many
        distinct values are seen; change detection still tracks the true
        range."""
        detector = ValueRangeDetector()
        tracker = SingleStabilityTracker()

        for v in [50, 10, 30, 90, 20, 70]:  # min=10, max=90
            detector.add_value(tracker, v)

        assert tracker.unique_set == {10, 90}
        # 50 (first, True), 10 (new min, True), 90 (new max, True) extend range;
        # 30, 20, 70 fall inside -> False
        assert list(tracker.change_series) == [True, True, False, True, False, False]


class TestValueRangeDetectorTraining:
    """Test ValueRangeDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = ValueRangeDetector(config=config, name="MultipleDetector")
        # Train with multiple values (the minimum and maximum value should be captured)
        min_val = 100000
        max_val = 0
        for event in range(3):
            for _ in range(300):
                value = random.randint(0, 300)
                if event == 1:
                    min_val = min(min_val, value)
                    max_val = max(max_val, value)
                parser_data = schemas.ParserSchema({
                    "parserType": "test",
                    "EventID": event,
                    "template": "test template",
                    "variables": ["val0", str(value), "val2", "val3", "val4"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "logFormatVariables": {}
                })
                detector.train(parser_data)

            for _ in range(300):
                value = random.uniform(0, 300)
                if event == 1:
                    min_val = min(min_val, value)
                    max_val = max(max_val, value)
                parser_data = schemas.ParserSchema({
                    "parserType": "test",
                    "EventID": event,
                    "template": "test template",
                    "variables": ["val0", str(value), "val2", "val3", "val4"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "logFormatVariables": {}
                })
                detector.train(parser_data)

        # Only event 1 should be tracked (based on events config)
        assert len(detector.persistency.events_data) == 1
        event_data = detector.persistency.get_event_data(1)
        assert event_data is not None
        # Check the variable at position 1 (named "test")
        assert min(event_data["test"].unique_set) == min_val
        assert max(event_data["test"].unique_set) == max_val

    def test_train_detect_non_numeric_raises(self):
        """Non-numeric values raise ValueError when ignore_non_numerical_val is
        False."""

        detector = ValueRangeDetector(config=config, name="CustomInit")
        # Train with multiple values (the minimum and maximum value should be captured)
        parser_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["val0", f"val{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {}
        })
        with pytest.raises(ValueError):
            detector.train(parser_data)
        normal_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["val0", f"{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {}
        })
        detector.train(normal_data)
        with pytest.raises(ValueError):
            output = schemas.DetectorSchema()
            detector.detect(parser_data, output)

    def test_train_detect_non_numeric_ignore(self):
        """Test training with non-numeric values and ignoring them."""

        detector = ValueRangeDetector(config=config, name="MultipleDetector")
        # Train with multiple values (the minimum and maximum value should be captured)
        parser_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["val0", f"val{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {}
        })
        detector.train(parser_data)
        normal_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["val0", f"{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {}
        })
        detector.train(normal_data)
        output = schemas.DetectorSchema()
        detector.detect(parser_data, output)


class TestValueRangeDetectorDetection:
    """Test ValueRangeDetector detection functionality."""

    def test_detect_learned_value_range_no_alert(self):
        detector = ValueRangeDetector(config=config, name="MultipleDetector")

        # Train with values
        for val in ["1", "5000", "2130"]:
            train_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": 1,
                "template": "test template",
                "variables": ["adsasd", val],
                "logID": "1",
                "parsedLogID": "1",
                "parserID": "test_parser",
                "log": "test log message",
                "logFormatVariables": {"level": "INFO"}
            })
            detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "4321"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.DetectorSchema()

        result = detector.detect(test_data, output)

        assert not result
        assert output.score == 0.0

    def test_detect_known_value_ranges_alert(self):
        detector = ValueRangeDetector(config=config, name="MultipleDetector")

        # Train with values
        for val in ["1", "5000", "2130"]:
            train_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": 1,
                "template": "test template",
                "variables": ["adsasd", val],
                "logID": "1",
                "parsedLogID": "1",
                "parserID": "test_parser",
                "log": "test log message",
                "logFormatVariables": {"level": "INFO"}
            })
            detector.train(train_data)

        # Detect with the different value
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "5001"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.DetectorSchema()

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0

        # Detect with the different value
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "0"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.DetectorSchema()

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0


_PARSER_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>:<Line>): <Content>",
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


class TestValueRangeDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = ValueRangeDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.configure(log)
        detector.set_configuration()

        for log in logs[:TRAIN_UNTIL]:
            logger.setLevel(logging.CRITICAL)
            detector.train(log)
            logger.setLevel(logging.DEBUG)

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        # uid is not always 0 for event id 0. uid=1002 in line 1864 is a different event id.
        assert detected_ids == {'1859', '1860', '1861', '1862'}


class TestValueRangeDetectorAutoConfig:
    """Test that process() drives configure/set_configuration/train/detect
    automatically."""

    def test_audit_log_anomalies_via_process(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = ValueRangeDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        # Phase 1: configure — keep configuring for logs[:TRAIN_UNTIL]
        detector.fitlogic.configure_state = ConfigState.KEEP_CONFIGURE
        for log in logs[:TRAIN_UNTIL]:
            detector.process(log)

        # Transition: stop configure so next process() call triggers set_configuration()
        detector.fitlogic.configure_state = ConfigState.STOP_CONFIGURE

        # Phase 2: train — keep training for logs[:TRAIN_UNTIL]
        detector.fitlogic.train_state = TrainState.KEEP_TRAINING
        for log in logs[:TRAIN_UNTIL]:
            logger.setLevel(logging.CRITICAL)
            detector.process(log)
            logger.setLevel(logging.DEBUG)

        # Phase 3: detect — stop training so process() only calls detect()
        detector.fitlogic.train_state = TrainState.STOP_TRAINING
        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            if detector.process(log) is not None:
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862'}


class TestValueRangeDetectorGlobalInstances:
    """Tests event-ID-independent global instance detection."""

    def test_global_instance_detects_new_type(self):
        """Global instance monitoring Type detects CRED_REFR, USER_AUTH,
        USER_CMD which only appear after the training window (line 1800+)."""
        parser = MatcherParser(config=_PARSER_CONFIG)
        config_dict = {
            "detectors": {
                "ValueRangeDetector": {
                    "method_type": "value_range_detector",
                    "auto_config": False,
                    "params": {"ignore_non_numerical_val": True},
                    "global": {
                        "test": {
                            "header_variables": [{"pos": "Time"}]
                        }
                    }
                }
            }
        }
        config = ValueRangeDetectorConfig.from_dict(config_dict, "ValueRangeDetector")
        detector = ValueRangeDetector(config=config)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        # Global tracker must be populated under the sentinel event ID
        assert GLOBAL_EVENT_ID in detector.persistency.get_events_data()

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                assert all(key.startswith("Global -") for key in output["alertsObtain"])
                detected_ids.add(log["logID"])

        assert len(detected_ids) > 0


class TestValueRangeDetectorPersistFixes:
    def test_registers_persistency_saver(self):
        """The detector wires persistency into the base saver hook (was
        missing)."""
        from detectmatelibrary.common.detector import PersistConfig

        detector = ValueRangeDetector(
            config=ValueRangeDetectorConfig(
                persist=PersistConfig(path="memory://value_range_regpersist/state")
            )
        )
        # _register_persistency builds a PersistencySaver bound to detector.persistency
        assert detector.saver is not None
        assert detector.saver._persistency is detector.persistency
        detector.saver.stop()

    def test_set_configuration_preserves_persist(self):
        """set_configuration keeps the persist config (was dropped)."""
        from detectmatelibrary.common.detector import PersistConfig

        detector = ValueRangeDetector()
        # Simulate persist being enabled by an earlier config load
        detector.config.persist = PersistConfig(path="memory://value_range_persist_flag/state")

        # Feed configure() with a couple of stable-variable samples
        for _ in range(5):
            sample = schemas.ParserSchema({
                "parserType": "test", "EventID": 1, "template": "t",
                "variables": ["123"], "logID": "x", "parsedLogID": "x",
                "parserID": "p", "log": "l",
                "logFormatVariables": {"level": "INFO"},
            })
            detector.configure(sample)

        detector.set_configuration()

        assert detector.config.persist is not None
        assert detector.config.persist.path == "memory://value_range_persist_flag/state"

    def test_tracker_reconstruction_does_not_start_saver(self, monkeypatch):
        """A tracker reconstructs a throwaway detector by name to recover its
        add_value closure; that throwaway must not start a PersistencySaver
        even when the serialized detector_config carries a persist section (it
        would leak a saver thread per variable and clobber the real state
        file)."""
        from detectmatelibrary.common.detector import PersistConfig
        from detectmatelibrary.utils.persistency import PersistencySaver
        from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker \
            import SingleStabilityTracker

        starts: list = []
        monkeypatch.setattr(PersistencySaver, "start", lambda self: starts.append(self))

        detector_config = ValueRangeDetectorConfig(
            auto_config=False,
            persist=PersistConfig(path="memory://value_range_recon_no_leak/state"),
        ).to_dict(method_id="ValueRangeDetector")
        # precondition: the serialized config carries a persist section
        assert "persist" in detector_config["detectors"]["ValueRangeDetector"]

        tracker = SingleStabilityTracker(
            add_value_fn="ValueRangeDetector", detector_config=detector_config
        )
        # reconstruction recovered the range-semantics add_value closure...
        tracker.add_value(5)
        assert 5 in tracker.unique_set
        # ...but started NO saver (the throwaway instance must not persist)
        assert starts == []
