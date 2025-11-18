"""Tests for NewValueDetector class.

This module tests the NewValueDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Hierarchical configuration handling (event-specific and "all" events)
- Input/output schema validation
"""

from detectmatelibrary.detectors.new_value_detector import NewValueDetector, BufferMode
import detectmatelibrary.schemas as schemas

from detectmatelibrary.utils.aux import time_test_mode


# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "new_value_detector",
            "auto_config": False,
            "params": {
                "log_variables": [{
                    "id": "instanace1",
                    "event": 1,
                    "template": "adsdas",
                    "variables": [{
                        "pos": 0, "name": "sad", "params": {}
                    }]
                }]
            }
        },
        "AllDetector": {
            "method_type": "new_value_detector",
            "auto_config": False,
            "params": {
                "all_log_variables": {
                    "variables": [{
                        "pos": 1, "name": "test", "params": {}
                    }],
                    "header_variables": [{
                        "pos": "level", "params": {}
                    }]
                }
            }
        },
        "MultipleDetector": {
            "method_type": "new_value_detector",
            "auto_config": False,
            "params": {
                "log_variables": [{
                    "id": "test",
                    "event": 1,
                    "template": "qwewqe",
                    "variables": [{
                        "pos": 1, "name": "test", "params": {}
                    }],
                    "header_variables": [{
                        "pos": "level", "params": {}
                    }]
                }]
            }
        }
    }
}


class TestNewValueDetectorInitialization:
    """Test NewValueDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = NewValueDetector()

        assert detector.name == "NewValueDetector"
        assert hasattr(detector, 'config')
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.PARSER_SCHEMA
        assert detector.output_schema == schemas.DETECTOR_SCHEMA
        assert hasattr(detector, 'known_values')

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        detector = NewValueDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert isinstance(detector.known_values, dict)


class TestNewValueDetectorTraining:
    """Test NewValueDetector training functionality."""

    def test_train_all_multiple_values(self):
        """Test training with multiple different values."""
        detector = NewValueDetector(config=config, name="AllDetector")

        # Train with multiple values
        for level in ["INFO", "WARNING", "ERROR"]:
            parser_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
                "parserType": "test",
                "EventID": 1,
                "template": "test template",
                "variables": ["0", "assa"],
                "logID": 1,
                "parsedLogID": 1,
                "parserID": "test_parser",
                "log": "test log message",
                "logFormatVariables": {"level": level}
            })
            detector.train(parser_data)

        # Verify all values were learned
        assert len(detector.known_values) == 2
        assert "INFO" in detector.known_values["level"]
        assert "WARNING" in detector.known_values["level"]
        assert "ERROR" in detector.known_values["level"]
        assert "assa" in detector.known_values[1]

    def test_train_multiple_values(self):
        """Test training with multiple different values."""
        detector = NewValueDetector(config=config, name="MultipleDetector")
        # Train with multiple values
        for event in range(3):
            for level in ["INFO", "WARNING", "ERROR"]:
                parser_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
                    "parserType": "test",
                    "EventID": event,
                    "template": "test template",
                    "variables": ["0", "assa"],
                    "logID": 1,
                    "parsedLogID": 1,
                    "parserID": "test_parser",
                    "log": "test log message",
                    "logFormatVariables": {"level": level}
                })
                detector.train(parser_data)

        assert len(detector.known_values) == 1
        assert "INFO" in detector.known_values[1]["level"]
        assert "WARNING" in detector.known_values[1]["level"]
        assert "ERROR" in detector.known_values[1]["level"]
        assert "assa" in detector.known_values[1][1]


class TestNewValueDetectorDetection:
    """Test NewValueDetector detection functionality."""

    def test_detect_known_value_no_alert_all(self):
        """Test that known values don't trigger alerts."""
        detector = NewValueDetector(config=config, name="AllDetector")

        # Train with a value
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
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
            "EventID": 12,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        # Should not trigger alert for known value
        assert not result
        assert output.score == 0.0

    def test_detect_known_value_alert_all(self):
        detector = NewValueDetector(config=config, name="AllDetector")

        # Train with a value
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
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
            "EventID": 12,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0

    def test_detect_known_value_no_alert(self):
        detector = NewValueDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
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
            "EventID": 12,
            "template": "test template",
            "variables": ["adsasd"],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        assert not result
        assert output.score == 0.0

    def test_detect_known_value_alert(self):
        detector = NewValueDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "asdasd"],
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
            "variables": ["adsasd", "asdasd"],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0
