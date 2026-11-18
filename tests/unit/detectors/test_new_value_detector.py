"""Tests for NewValueDetector class.

This module tests the NewValueDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.detectors.new_value_detector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc
from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

from copy import deepcopy

import pytest

# Set time test mode for consistent timestamps
pytestmark = pytest.mark.usefixtures("frozen_timestamps")


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "new_value_detector",
            "auto_config": False,
            "params": {},
            "events": {
                1: {
                    "instance1": {
                        "params": {},
                        "variables": [{
                            "pos": 0, "name": "sad", "params": {}
                        }]
                    }
                }
            }
        },
        "MultipleDetector": {
            "method_type": "new_value_detector",
            "auto_config": False,
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 1, "name": "test", "params": {}
                        }],
                        "header_variables": [{
                            "pos": "level", "params": {}
                        }]
                    }
                }
            }
        }
    }
}


def _event_1_record(log_id: str, value: str) -> sc.ParserSchema:
    return sc.ParserSchema({
        "parserType": "test", "eventID": 1, "template": "test template", "variables": ["adsasd", value],
        "logID": log_id, "parsedLogID": log_id, "parserID": "test_parser", "log": "test log message",
        "headerVariables": {"level": "INFO"},
    })


class TestNewValueDetectorTraining:
    """Test NewValueDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = NewValueDetector(config=config, name="MultipleDetector")
        # Train with multiple values (only event 1 should be tracked per config)
        for event in range(3):
            for level in ["INFO", "WARNING", "ERROR"]:
                parser_data = sc.ParserSchema({
                    "parserType": "test",
                    "eventID": event,
                    "template": "test template",
                    "variables": ["0", "assa"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "headerVariables": {"level": level}
                })
                detector.train(parser_data)

        # Only event 1 should be tracked (based on events config)
        assert len(detector.persistency) == 1
        event_data = detector.persistency.get_event_data(1)
        assert event_data is not None
        # Check the level values
        assert "INFO" in event_data["level"].unique_set
        assert "WARNING" in event_data["level"].unique_set
        assert "ERROR" in event_data["level"].unique_set
        # Check the variable at position 1 (named "test")
        assert "assa" in event_data["test"].unique_set


class TestNewValueDetectorDetection:
    """Test NewValueDetector detection functionality."""

    def test_detect_ignores_unconfigured_event(self):
        detector = NewValueDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # EventID 12 is not in the config, so nothing is checked
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 12,
            "template": "test template",
            "variables": ["adsasd"],
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

    def test_detect_known_value_no_alert(self):
        """Event 1 checks variable 1 and the header `level` (module config)."""
        detector = NewValueDetector(config=config, name="MultipleDetector")
        detector.train(_event_1_record("1", "asdasd"))

        assert detector.detect(_event_1_record("2", "asdasd"), sc.DetectorSchema()) is False
        assert detector.detect(_event_1_record("3", "qwqwqw"), sc.DetectorSchema()) is True

    def test_detect_known_value_alert(self):
        detector = NewValueDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
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
            "variables": ["adsasd", "asdasd"],
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
            "log_format": "type=<Type> msg=audit(<Time>): <Content>",
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


class TestNewValueDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.slow
    def test_audit_log_anomalies_to_binary(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = NewValueDetector(config=NewValueDetectorConfig(allow_fed=True))
        detector2 = NewValueDetector(config=NewValueDetectorConfig(allow_fed=True))

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

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}

    @pytest.mark.slow
    def test_audit_log_anomalie_fed(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector1 = NewValueDetector(config=NewValueDetectorConfig(allow_fed=True))
        detector2 = NewValueDetector(config=NewValueDetectorConfig(allow_fed=True))

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs[:TRAIN_UNTIL]:
            detector1.configure(log)
            detector2.configure(log)

        detector1.set_configuration()
        detector2.set_configuration()

        for i, log in enumerate(logs[:TRAIN_UNTIL]):
            if i < 10:
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

        assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}


class TestNewValueDetectorAutoConfig:
    """Test that process() drives configure/set_configuration/train/detect
    automatically."""

    def test_auto_config_off_keeps_explicit_events_through_configure_phase(self):
        """A configure window must not overwrite a hand-written `events` block
        when auto_config is False — the config has to reproduce the same
        detector on every rerun."""
        windowed = deepcopy(config)
        windowed["detectors"]["CustomInit"].update(data_use_configure=5, data_use_training=5)
        detector = NewValueDetector(config=windowed, name="CustomInit")
        explicit_events = detector.config.events.model_dump()

        for i in range(20):
            detector.process(sc.ParserSchema({
                "parserType": "test",
                "eventID": [1, 2, 3][i % 3],
                "template": "test template",
                "variables": ["same", str(i)],
                "logID": str(i),
                "parsedLogID": str(i),
                "parserID": "test_parser",
                "log": "test log message",
                "headerVariables": {"level": "INFO", "Time": str(1_700_000_000 + i)},
            }))

        assert detector.config.events.model_dump() == explicit_events
        assert detector.config.auto_config is False
        # the configure window still reached training under the explicit config
        assert "same" in detector.persistency.get_events_data()[1].get_data()["sad"].unique_set
