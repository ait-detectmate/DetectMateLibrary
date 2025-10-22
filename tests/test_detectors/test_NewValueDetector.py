"""Tests for NewValueDetector class.

This module tests the NewValueDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Hierarchical configuration handling (event-specific and "all" events)
- Input/output schema validation
"""

from components.common.config.detector import DetectorInstance, DetectorVariable
from components.detectors.NewValueDetector import NewValueDetector, NewValueDetectorConfig
from components.common.config.detector import CoreDetectorConfig
import schemas as schemas
from utils.aux import time_test_mode


# Set time test mode for consistent timestamps
time_test_mode()


class TestNewValueDetectorInitialization:
    """Test NewValueDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = NewValueDetector()

        assert detector.name == "NewValueDetector"
        assert hasattr(detector, 'config')
        assert detector.data_buffer.mode == "no_buf"
        assert detector.input_schema == schemas.PARSER_SCHEMA
        assert detector.output_schema == schemas.DETECTOR_SCHEMA
        assert hasattr(detector, 'known_values')

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        config = CoreDetectorConfig(
            detectorID="TestNewValueDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event=1,
                    variables=[
                        DetectorVariable(pos=0, params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(name="TestDetector", config=config)

        assert detector.name == "TestDetector"
        assert detector.config.detectorID == "TestNewValueDetector"
        assert detector.config.detectorType == "NewValueDetector"
        # Check that known_values structure is initialized
        assert isinstance(detector.known_values, dict)


class TestNewValueDetectorTraining:
    """Test NewValueDetector training functionality."""

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        config = CoreDetectorConfig(
            detectorID="TestDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event="all",
                    variables=[
                        DetectorVariable(pos="level", params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(config=config)

        # Train with multiple values
        for level in ["INFO", "WARNING", "ERROR"]:
            parser_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
                "parserType": "test",
                "EventID": 1,
                "template": "test template",
                "variables": [],
                "logID": 1,
                "parsedLogID": 1,
                "parserID": "test_parser",
                "log": "test log message",
                "logFormatVariables": {"level": level}
            })
            detector.train(parser_data)

        # Verify all values were learned
        assert "INFO" in detector.known_values["all"]["level"]
        assert "WARNING" in detector.known_values["all"]["level"]
        assert "ERROR" in detector.known_values["all"]["level"]


class TestNewValueDetectorDetection:
    """Test NewValueDetector detection functionality."""

    def test_detect_known_value_no_alert(self):
        """Test that known values don't trigger alerts."""
        config = CoreDetectorConfig(
            detectorID="TestDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event="all",
                    variables=[
                        DetectorVariable(pos="level", params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(config=config)

        # Train with a value
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": [],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": [],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        # Should not trigger alert for known value
        assert result is False
        assert output.score == 0.0

    def test_detect_new_value_triggers_alert(self):
        """Test that new/unknown values trigger alerts."""
        config = CoreDetectorConfig(
            detectorID="TestDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event="all",
                    variables=[
                        DetectorVariable(pos="level", params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(config=config)

        # Train with a value
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": [],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Detect with a NEW value
        test_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": [],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        # Should trigger alert for new value
        assert result is True
        assert output.score > 0.0
        assert "CRITICAL" in output.alertsObtain

    def test_detect_with_variable_positions(self):
        """Test detection with variable positions (list indices)."""
        config = CoreDetectorConfig(
            detectorID="TestDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event="all",
                    variables=[
                        DetectorVariable(pos=0, params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(config=config)

        # Train with a value at position 0
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template <*>",
            "variables": ["value1"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message value1",
            "logFormatVariables": {}
        })
        detector.train(train_data)

        # Detect with a new value
        test_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template <*>",
            "variables": ["value2"],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message value2",
            "logFormatVariables": {}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        # Should trigger alert for new value
        assert result is True
        assert output.score > 0.0


class TestNewValueDetectorEventSpecific:
    """Test event-specific configuration handling."""

    def test_all_events_and_specific_event(self):
        """Test combination of 'all' events and event-specific
        configuration."""
        config = CoreDetectorConfig(
            detectorID="TestDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event="all",
                    variables=[
                        DetectorVariable(pos="level", params=NewValueDetectorConfig())
                    ]
                ),
                DetectorInstance(
                    id="instance2",
                    event=1,
                    variables=[
                        DetectorVariable(pos=0, params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(config=config)

        # Train with both level and variable
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template <*>",
            "variables": ["var1"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message var1",
            "logFormatVariables": {"level": "INFO"}
        })
        detector.train(train_data)

        # Verify both were learned
        assert "INFO" in detector.known_values["all"]["level"]
        assert "var1" in detector.known_values[1][0]


class TestNewValueDetectorIntegration:
    """Integration tests for NewValueDetector with full pipeline."""

    def test_full_train_and_detect_pipeline(self):
        """Test complete training and detection pipeline."""
        config = CoreDetectorConfig(
            detectorID="TestDetector",
            detectorType="NewValueDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event="all",
                    variables=[
                        DetectorVariable(pos="level", params=NewValueDetectorConfig())
                    ]
                )
            ]
        )
        detector = NewValueDetector(config=config)

        # Train with multiple logs
        training_logs = [
            {"level": "INFO", "logID": 1},
            {"level": "INFO", "logID": 2},
            {"level": "WARNING", "logID": 3},
            {"level": "ERROR", "logID": 4},
        ]

        for log in training_logs:
            train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
                "parserType": "test",
                "EventID": 1,
                "template": "test template",
                "variables": [],
                "logID": log["logID"],
                "parsedLogID": log["logID"],
                "parserID": "test_parser",
                "log": "test log message",
                "logFormatVariables": {"level": log["level"]}
            })
            detector.train(train_data)

        # Test detection on known value (should not alert)
        test_known = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": [],
            "logID": 5,
            "parsedLogID": 5,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        output_known = schemas.initialize(schemas.DETECTOR_SCHEMA)
        alert = detector.detect(test_known, output_known)
        assert alert is False

        # Test detection on new value (should alert)
        test_new = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": [],
            "logID": 6,
            "parsedLogID": 6,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output_new = schemas.initialize(schemas.DETECTOR_SCHEMA)
        alert = detector.detect(test_new, output_new)
        assert alert is True
        assert output_new.score > 0.0
