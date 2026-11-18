"""Tests for ValueRangeDetector class.

This module tests the ValueRangeDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Event-specific configuration handling
- Input/output schema validation
"""
import pytest
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetector, ValueRangeDetectorConfig
from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc
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


def _record(value: str, event_id: int = 1) -> sc.ParserSchema:
    """A log of `event_id` whose variable 1 (named "test") is `value`."""
    return sc.ParserSchema({
        "parserType": "test", "eventID": event_id, "template": "test template",
        "variables": ["val0", value, "val2", "val3", "val4"], "logID": "1", "parsedLogID": "1",
        "parserID": "test_parser", "log": "test log message", "headerVariables": {},
    })


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
        """Only event 1 is configured; its variable keeps the minimum and
        maximum of ints and floats."""
        detector = ValueRangeDetector(config=config, name="MultipleDetector")
        for event in range(3):
            for value in ["17", "250", "3", "300", "0.5", "299.75"]:
                detector.train(_record(value, event))

        assert len(detector.persistency) == 1
        assert detector.persistency.get_event_data(1)["test"].unique_set == {0.5, 300}

    def test_train_detect_non_numeric_raises(self):
        """Non-numeric values raise ValueError when ignore_non_numerical_val is
        False."""
        detector = ValueRangeDetector(config=config, name="CustomInit")
        with pytest.raises(ValueError):
            detector.train(_record("val17"))

        detector.train(_record("17"))
        with pytest.raises(ValueError):
            detector.detect(_record("val17"), sc.DetectorSchema())

    def test_train_detect_non_numeric_ignore(self):
        """With ignore_non_numerical_val, non-numeric values are neither
        learned nor alerted on."""
        detector = ValueRangeDetector(config=config, name="MultipleDetector")
        detector.train(_record("val17"))
        detector.train(_record("17"))

        assert detector.persistency.get_event_data(1)["test"].unique_set == {17}
        assert detector.detect(_record("val17"), sc.DetectorSchema()) is False
        assert detector.detect(_record("18"), sc.DetectorSchema()) is True


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
