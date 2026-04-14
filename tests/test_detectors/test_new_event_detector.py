"""Tests for NewEventDetector class.

This module tests the NewEventDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Event-specific configuration handling
- Input/output schema validation
"""

import json

from detectmatelibrary.detectors.new_event_detector import NewEventDetector, NewEventDetectorConfig, \
    BufferMode
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas

from detectmatelibrary.utils.aux import time_test_mode
from detectmatelibrary.common._core_op._fit_logic import ConfigState, TrainState
from detectmatelibrary.constants import GLOBAL_EVENT_ID


# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {}
        },
        "MultipleDetector": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {}
        },
        "NewEventDetector": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {}
        }
    }
}


class TestNewEventDetectorInitialization:
    """Test NewEventDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = NewEventDetector()

        assert detector.name == "NewEventDetector"
        assert hasattr(detector, 'config')
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema
        assert hasattr(detector, 'persistency')

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        detector = NewEventDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert hasattr(detector, 'persistency')
        assert isinstance(detector.persistency.events_data, dict)


class TestNewEventDetectorTraining:
    """Test NewEventDetector training functionality."""

    def test_train_multiple_event_ids(self):
        """Test training with multiple different event ids."""
        detector = NewEventDetector(config=config, name="MultipleDetector")
        event_ids = {0, 3, 8, 9}
        for event in event_ids:
            parser_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": event,
                "template": "test template",
                "variables": ["0", "assa"],
                "logID": "1",
                "parsedLogID": "1",
                "parserID": "test_parser",
                "log": "test log message",
                "logFormatVariables": {"level": "INFO"}
            })
            detector.train(parser_data)

        assert len(detector.persistency.events_seen) == len(event_ids)
        event_seen = detector.persistency.get_events_seen()
        assert event_seen == event_ids


class TestNewEventDetectorDetection:
    """Test NewEventDetector detection functionality."""

    def test_detect_known_event_id_no_alert(self):
        detector = NewEventDetector(config=config, name="MultipleDetector")

        # Train with an event_id
        train_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Detect with the same event_id
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd"],
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
                "path_templates": "tests/test_folder/audit_templates.txt",
            },
        }
    }
}


class TestNewEventDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = NewEventDetector(config=config, name="NewEventDetector")

        logs = list(From.log(parser, in_path="tests/test_folder/audit.log", do_process=True))

        for log in logs[:1800]:
            detector.configure(log)
        detector.set_configuration()

        for log in logs[:1800]:
            detector.train(log)

        detected_ids: set[str] = set()
        for i, log in enumerate(logs[1800:]):
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        assert detected_ids == {"1863"}


class TestNewEventDetectorAutoConfig:
    """Test that process() drives configure/set_configuration/train/detect
    automatically."""

    def test_audit_log_anomalies_via_process(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = NewEventDetector()

        logs = list(From.log(parser, in_path="tests/test_folder/audit.log", do_process=True))

        # Phase 1: configure — keep configuring for logs[:1800]
        detector.fitlogic.configure_state = ConfigState.KEEP_CONFIGURE
        for log in logs[:1800]:
            detector.process(log)

        # Transition: stop configure so next process() call triggers set_configuration()
        detector.fitlogic.configure_state = ConfigState.STOP_CONFIGURE

        # Phase 2: train — keep training for logs[:1800]
        detector.fitlogic.train_state = TrainState.KEEP_TRAINING
        for log in logs[:1800]:
            detector.process(log)

        print(json.dumps(detector.config.get_config(), indent=2))

        # Phase 3: detect — stop training so process() only calls detect()
        detector.fitlogic.train_state = TrainState.STOP_TRAINING
        detected_ids: set[str] = set()
        for log in logs[1800:]:
            if detector.process(log) is not None:
                detected_ids.add(log["logID"])

        assert detected_ids == {"1863"}


class TestNewEventDetectorGlobalInstances:
    """Tests event-ID-independent global instance detection."""

    def test_global_instance_detects_new_type(self):
        """Global instance monitoring Type detects CRED_REFR, USER_AUTH,
        USER_CMD which only appear after the training window (line 1800+)."""
        parser = MatcherParser(config=_PARSER_CONFIG)
        config_dict = {
            "detectors": {
                "NewEventDetector": {
                    "method_type": "new_event_detector",
                    "auto_config": False,
                    "global": {
                        "test": {
                            "header_variables": [{"pos": "Type"}]
                        }
                    }
                }
            }
        }
        config = NewEventDetectorConfig.from_dict(config_dict, "NewEventDetector")
        detector = NewEventDetector(config=config)

        logs = list(From.log(parser, in_path="tests/test_folder/audit.log", do_process=True))

        for log in logs[:1800]:
            detector.train(log)

        # Global tracker must be populated under the sentinel event ID
        assert GLOBAL_EVENT_ID in detector.persistency.get_events_seen()

        detected_ids: set[str] = set()
        for log in logs[1800:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                assert all(key.startswith("Global -") for key in output["alertsObtain"])
                detected_ids.add(log["logID"])

        assert len(detected_ids) > 0
