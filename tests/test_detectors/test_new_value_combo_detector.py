
from detectmatelibrary.detectors.new_value_combo_detector import (
    NewValueComboDetector, ComboTooBigError, BufferMode
)
import detectmatelibrary.schemas as schemas

from detectmatelibrary.utils.aux import time_test_mode

import pytest

# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 4,
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
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 2,
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
        "AllDetectorTooBig": {
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 5,
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
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 2,
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
        },
        "MultipleDetectorTooBig": {
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 5,
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


class TestNewValueComboDetectorInitialization:

    def test_default_initialization(self):
        detector = NewValueComboDetector()

        assert detector.name == "NewValueComboDetector"
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema_
        assert detector.output_schema == schemas.DetectorSchema_

    def test_custom_config_initialization(self):
        detector = NewValueComboDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert detector.config.comb_size == 4
        assert isinstance(detector.known_combos, dict)


class TestNewValueComboDetectorTraining:

    def test_train_all_multiple_values(self):
        detector = NewValueComboDetector(config=config, name="AllDetector")

        # Train with multiple values
        for level in ["INFO", "WARNING", "ERROR"]:
            parser_data = schemas.ParserSchema_({
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

        combos = {"all": set({
            ("assa", "INFO"), ("assa", "WARNING"), ("assa", "ERROR")
        })}
        assert combos == detector.known_combos

    def test_train_multiple_values(self):
        detector = NewValueComboDetector(config=config, name="MultipleDetector")

        # Train with multiple values
        for event in range(3):
            for level in ["INFO", "WARNING", "ERROR"]:
                parser_data = schemas.ParserSchema_({
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

        combos = {"all": set(), 1: set({
            ("assa", "INFO"), ("assa", "WARNING"), ("assa", "ERROR")
        })}
        assert combos == detector.known_combos

    def test_train_too_big(self):
        parser_data = schemas.ParserSchema_({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["0", "assa"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "INFO"}
        })

        with pytest.raises(ComboTooBigError):
            detector = NewValueComboDetector(config=config, name="AllDetectorTooBig")
            detector.train(parser_data)

        with pytest.raises(ComboTooBigError):
            detector = NewValueComboDetector(config=config, name="MultipleDetectorTooBig")
            detector.train(parser_data)


class TestNewValueComboDetectorDetection:
    """Test NewValueDetector detection functionality."""

    def test_detect_known_value_no_alert_all(self):
        """Test that known values don't trigger alerts."""
        detector = NewValueComboDetector(config=config, name="AllDetector")

        # Train with a value
        train_data = schemas.ParserSchema_({
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

        train_data = schemas.ParserSchema_({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "other_value"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema_({
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
        output = schemas.DetectorSchema_()

        result = detector.detect(test_data, output)

        # Should not trigger alert for known value
        assert not result
        assert output.score == 0.0

    def test_detect_known_value_alert_all(self):
        detector = NewValueComboDetector(config=config, name="AllDetector")

        # Train with a value
        train_data = schemas.ParserSchema_({
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

        train_data = schemas.ParserSchema_({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "other_value"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema_({
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
        output = schemas.DetectorSchema_()

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0

    def test_detect_known_value_no_alert(self):
        detector = NewValueComboDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = schemas.ParserSchema_({
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

        train_data = schemas.ParserSchema_({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "other_value"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema_({
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
        output = schemas.DetectorSchema_()

        result = detector.detect(test_data, output)

        assert not result
        assert output.score == 0.0

    def test_detect_known_value_alert(self):
        detector = NewValueComboDetector(config=config, name="MultipleDetector")

        # Train with a value
        train_data = schemas.ParserSchema_({
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

        train_data = schemas.ParserSchema_({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "other_value"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema_({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd"],
            "logID": 2,
            "parsedLogID": 2,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        output = schemas.DetectorSchema_()

        result = detector.detect(test_data, output)

        assert result
        assert output.score == 1.0
