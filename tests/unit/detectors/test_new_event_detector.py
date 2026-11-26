"""Tests for NewEventDetector class.

This module tests the NewEventDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.detectors.new_event_detector import NewEventDetector
import detectmatelibrary.schemas as sc

import pytest

# Set time test mode for consistent timestamps
pytestmark = pytest.mark.usefixtures("frozen_timestamps")


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


class TestNewEventDetectorTraining:
    """Test NewEventDetector training functionality."""

    def test_train_multiple_event_ids(self):
        """Test training with multiple different event ids."""
        detector = NewEventDetector(config=config, name="MultipleDetector")
        event_ids = {0, 3, 8, 9}
        for event in event_ids:
            parser_data = sc.ParserSchema({
                "parserType": "test",
                "eventID": event,
                "template": "test template",
                "variables": ["0", "assa"],
                "logID": "1",
                "parsedLogID": "1",
                "parserID": "test_parser",
                "log": "test log message",
                "headerVariables": {"level": "INFO"}
            })
            detector.train(parser_data)

        assert len(detector.persistency.get_events_seen()) == len(event_ids)
        event_seen = detector.persistency.get_events_seen()
        assert event_seen == event_ids


class TestNewEventDetectorDetection:
    """Test NewEventDetector detection functionality."""

    def test_detect_known_event_id_no_alert(self):
        detector = NewEventDetector(config=config, name="MultipleDetector")

        # Train with an event_id
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

        # Detect with the same event_id
        test_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
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
