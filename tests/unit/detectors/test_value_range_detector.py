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
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetector, ValueRangeDetectorConfig
from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)
from detectmatelibrary.common._core_op._fit_logic import EnumState
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc
from detectmatelibrary.tools.logging import logger
from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES
# Set time test mode for consistent timestamps
pytestmark = pytest.mark.usefixtures("frozen_timestamps")


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


class TestValueRangeDetectorAddValue:
    """add_value() applies range semantics to the trackers."""

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
                parser_data = sc.ParserSchema({
                    "parserType": "test",
                    "eventID": event,
                    "template": "test template",
                    "variables": ["val0", str(value), "val2", "val3", "val4"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "headerVariables": {}
                })
                detector.train(parser_data)

            for _ in range(300):
                value = random.uniform(0, 300)
                if event == 1:
                    min_val = min(min_val, value)
                    max_val = max(max_val, value)
                parser_data = sc.ParserSchema({
                    "parserType": "test",
                    "eventID": event,
                    "template": "test template",
                    "variables": ["val0", str(value), "val2", "val3", "val4"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "headerVariables": {}
                })
                detector.train(parser_data)

        # Only event 1 should be tracked (based on events config)
        assert len(detector.persistency) == 1
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
        parser_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["val0", f"val{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {}
        })
        with pytest.raises(ValueError):
            detector.train(parser_data)
        normal_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["val0", f"{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {}
        })
        detector.train(normal_data)
        with pytest.raises(ValueError):
            output = sc.DetectorSchema()
            detector.detect(parser_data, output)

    def test_train_detect_non_numeric_ignore(self):
        """Test training with non-numeric values and ignoring them."""

        detector = ValueRangeDetector(config=config, name="MultipleDetector")
        # Train with multiple values (the minimum and maximum value should be captured)
        parser_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["val0", f"val{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {}
        })
        detector.train(parser_data)
        normal_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["val0", f"{random.randint(0, 300)}", "val2", "val3", "val4"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {}
        })
        detector.train(normal_data)
        output = sc.DetectorSchema()
        detector.detect(parser_data, output)


class TestValueRangeDetectorDetection:
    """Test ValueRangeDetector detection functionality."""

    def test_detect_learned_value_range_no_alert(self):
        detector = ValueRangeDetector(config=config, name="MultipleDetector")

        # Train with values
        for val in ["1", "5000", "2130"]:
            train_data = sc.ParserSchema({
                "parserType": "test",
                "eventID": 1,
                "template": "test template",
                "variables": ["adsasd", val],
                "logID": "1",
                "parsedLogID": "1",
                "parserID": "test_parser",
                "log": "test log message",
                "headerVariables": {"level": "INFO"}
            })
            detector.train(train_data)

        # Detect with the same value
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "4321"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "CRITICAL"}
        })
        output = sc.DetectorSchema()

        result = detector.detect(test_data, output)

        assert not result
        assert output.score == 0.0

    def test_detect_known_value_ranges_alert(self):
        detector = ValueRangeDetector(config=config, name="MultipleDetector")

        # Train with values
        for val in ["1", "5000", "2130"]:
            train_data = sc.ParserSchema({
                "parserType": "test",
                "eventID": 1,
                "template": "test template",
                "variables": ["adsasd", val],
                "logID": "1",
                "parsedLogID": "1",
                "parserID": "test_parser",
                "log": "test log message",
                "headerVariables": {"level": "INFO"}
            })
            detector.train(train_data)

        # Detect with the different value
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "5001"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "CRITICAL"}
        })
        output = sc.DetectorSchema()

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0

        # Detect with the different value
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "0"],
            "logID": "2",
            "parsedLogID": "2",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "CRITICAL"}
        })
        output = sc.DetectorSchema()

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

    @pytest.mark.slow
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
            output = sc.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        # uid is not always 0 for event id 0. uid=1002 in line 1864 is a different event id.
        assert detected_ids == {'1859', '1860', '1861', '1862'}

    @pytest.mark.slow
    def test_audit_log_anomalies_to_binary(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = ValueRangeDetector(config=ValueRangeDetectorConfig(allow_fed=True))
        detector2 = ValueRangeDetector(config=ValueRangeDetectorConfig(allow_fed=True))

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.configure(log)
            detector2.configure(log)

        detector.set_configuration()
        detector2.set_configuration()

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        detector2 = detector2.from_binary(detector.to_binary())
        assert detector2.persistency == detector.persistency

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = sc.DetectorSchema()
            if detector2.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862'}

    @pytest.mark.slow
    def test_audit_log_anomalie_fed(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector1 = ValueRangeDetector(config=ValueRangeDetectorConfig(allow_fed=True))
        detector2 = ValueRangeDetector(config=ValueRangeDetectorConfig(allow_fed=True))

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs[:TRAIN_UNTIL]:
            detector1.configure(log)
            detector2.configure(log)

        detector1.set_configuration()
        detector2.set_configuration()

        for i, log in enumerate(logs[:TRAIN_UNTIL]):
            if i < 1:
                detector1.train(log)
            else:
                detector2.train(log)

        assert detector2.persistency != detector1.persistency

        (detector1 + detector2).aggregate()
        assert detector2.persistency == detector1.persistency
        assert len(detector2.persistency) != 0

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = sc.DetectorSchema()
            if detector1.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {'1859', '1860', '1861', '1862'}


class TestValueRangeDetectorAutoConfig:
    """Test that process() drives configure/set_configuration/train/detect
    automatically."""

    @pytest.mark.slow
    def test_audit_log_anomalies_via_process(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = ValueRangeDetector()

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))

        # Phase 1: configure — keep configuring for logs[:TRAIN_UNTIL]
        detector.fitlogic.config_state.current = EnumState.KEEP
        for log in logs[:TRAIN_UNTIL]:
            detector.process(log)

        # Transition: stop configure so next process() call triggers set_configuration()
        detector.fitlogic.config_state.current = EnumState.STOP

        # Phase 2: train — keep training for logs[:TRAIN_UNTIL]
        detector.fitlogic.train_state.current = EnumState.KEEP
        for log in logs[:TRAIN_UNTIL]:
            logger.setLevel(logging.CRITICAL)
            detector.process(log)
            logger.setLevel(logging.DEBUG)

        # Phase 3: detect — stop training so process() only calls detect()
        detector.fitlogic.train_state.current = EnumState.STOP
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
            output = sc.DetectorSchema()
            if detector.detect(log, output_=output):
                assert all(key.startswith("Global -") for key in output["alertDetails"])
                detected_ids.add(log["logID"])

        assert len(detected_ids) > 0
