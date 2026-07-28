"""Tests for NewSequenceDetector class.

This module tests the NewSequenceDetector implementation including:
- Initialization and configuration
- Training functionality to learn known EventID sequences
- Detection logic for unknown sequences
- Window handling (reset_window) and end-to-end regression on audit.log
"""

from detectmatelibrary.detectors.new_sequence_detector import NewSequenceDetector, \
    NewSequenceDetectorConfig, BufferMode
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas
from detectmatelibrary.utils.aux import time_test_mode
from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "new_sequence_detector",
            "auto_config": False,
            "params": {
                "max_sequence_length": 2
            }
        },
        "MultipleDetector": {
            "method_type": "new_sequence_detector",
            "auto_config": False,
            "params": {
                "max_sequence_length": 2
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


class TestNewSequenceDetectorInitialization:
    """Test NewSequenceDetector initialization and configuration."""

    def test_default_initialization(self):
        detector = NewSequenceDetector()

        assert detector.name == "NewSequenceDetector"
        assert hasattr(detector, "config")
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema
        assert hasattr(detector, "persistency")
        assert detector.config.max_sequence_length == 3

    def test_custom_config_initialization(self):
        detector = NewSequenceDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert detector.config.max_sequence_length == 2
        assert hasattr(detector, "persistency")
        assert isinstance(detector.persistency.events_data, dict)


class TestNewSequenceDetectorTraining:
    """Test NewSequenceDetector training functionality."""

    def test_train_learns_sequence(self):
        detector = NewSequenceDetector(config=config, name="MultipleDetector")

        for event_id in [1, 2, 3]:
            detector.train(_make_schema(event_id))

        # max_sequence_length=2 -> sequences (1, 2) and (2, 3) are learned
        assert detector.get_known_sequences() == {("1", "2"), ("2", "3")}

    def test_train_below_window_length_learns_nothing(self):
        detector = NewSequenceDetector(config=config, name="MultipleDetector")

        # Only one event seen so far, window not yet full (max_sequence_length=2)
        detector.train(_make_schema(1))

        assert detector.get_known_sequences() == set()


class TestNewSequenceDetectorDetection:
    """Test NewSequenceDetector detection functionality."""

    def test_detect_known_sequence_no_alert(self):
        detector = NewSequenceDetector(config=config, name="MultipleDetector")

        # Repeating the cycle 1 -> 2 -> 3 teaches sequences (1,2), (2,3), (3,1)
        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_make_schema(event_id))
        # Window now holds the tail (2, 3); appending 1 reproduces the known (3, 1)
        output = schemas.DetectorSchema()
        result = detector.detect(_make_schema(1, log_id="7"), output)

        assert not result
        assert output.score == 0.0

    def test_detect_unknown_sequence_alert(self):
        detector = NewSequenceDetector(config=config, name="MultipleDetector")

        for event_id in [1, 2, 3, 1, 2, 3]:
            detector.train(_make_schema(event_id))

        # (3, 9) was never seen during training
        output = schemas.DetectorSchema()
        result = detector.detect(_make_schema(9, log_id="7"), output)

        assert result
        assert output.score == 1.0
        assert any("Sequence" in key for key in output["alertsObtain"])

    def test_detect_below_window_length_no_alert(self):
        detector = NewSequenceDetector(config=config, name="MultipleDetector")

        # First event with an empty detector: window not yet full, can't be an anomaly
        output = schemas.DetectorSchema()
        result = detector.detect(_make_schema(1), output)

        assert not result
        assert output.score == 0.0


class TestNewSequenceDetectorWindow:
    """Test sliding-window behaviour."""

    def test_reset_window_clears_state(self):
        detector = NewSequenceDetector(config=config, name="MultipleDetector")

        detector.train(_make_schema(1))
        assert len(detector._window) == 1

        detector.reset_window()
        assert len(detector._window) == 0


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


class TestNewSequenceDetectorEndToEnd:
    """Regression test: full train/detect pipeline on audit.log."""

    def test_audit_log_anomalies(self):
        pars = MatcherParser(config=_PARSER_CONFIG)
        detector = NewSequenceDetector(
            config=NewSequenceDetectorConfig(auto_config=False),
            name="NewSequenceDetector",
        )

        logs = list(From.log(pars, in_path=AUDIT_LOG, do_process=True))

        for log in logs[:TRAIN_UNTIL]:
            detector.train(log)

        detected_ids: set[str] = set()
        for log in logs[TRAIN_UNTIL:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {"1863", "1864", "1865"}
