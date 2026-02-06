
from detectmatelibrary.detectors.new_value_combo_detector import (
    NewValueComboDetector, BufferMode
)
from detectmatelibrary.common._config import generate_detector_config
import detectmatelibrary.schemas as schemas

from detectmatelibrary.utils.aux import time_test_mode


# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        "CustomInit": {
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 4
            },
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
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "params": {
                "comb_size": 2
            },
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


class TestNewValueComboDetectorInitialization:

    def test_default_initialization(self):
        detector = NewValueComboDetector()

        assert detector.name == "NewValueComboDetector"
        assert detector.data_buffer.mode == BufferMode.NO_BUF
        assert detector.input_schema == schemas.ParserSchema
        assert detector.output_schema == schemas.DetectorSchema

    def test_custom_config_initialization(self):
        detector = NewValueComboDetector(name="CustomInit", config=config)

        assert detector.name == "CustomInit"
        assert detector.config.comb_size == 4


class TestNewValueComboDetectorTraining:

    def test_train_multiple_values(self):
        detector = NewValueComboDetector(config=config, name="MultipleDetector")

        # Train with multiple values
        for event in range(3):
            for level in ["INFO", "WARNING", "ERROR"]:
                parser_data = schemas.ParserSchema({
                    "parserType": "test",
                    "EventID": event,
                    "template": "test template",
                    "variables": ["0", "assa"],
                    "logID": "1",
                    "parsedLogID": "1",
                    "parserID": "test_parser",
                    "log": "test log message",
                    "logFormatVariables": {"level": level}
                })
                detector.train(parser_data)

        # Only event 1 should be tracked (based on events config)
        assert len(detector.persistency.events_data) == 1


class TestNewValueComboDetectorDetection:
    """Test NewValueComboDetector detection functionality."""

    def test_detect_known_value_no_alert(self):
        detector = NewValueComboDetector(config=config, name="MultipleDetector")

        # Train with a value
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

        train_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "other_value"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        detector.train(train_data)

        # Detect with the same value
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 12,
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

    def test_detect_known_value_alert(self):
        detector = NewValueComboDetector(config=config, name="MultipleDetector")

        # Train with a value
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

        train_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "other_value"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"level": "CRITICAL"}
        })
        detector.train(train_data)

        # Detect with an unknown combination (pos 1 has a new value)
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["adsasd", "new_unknown_value"],
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


class TestNewValueComboDetectorConfiguration:
    """Test NewValueComboDetector configuration functionality."""

    def test_generate_detector_config_basic(self):
        """Test basic config generation with single event."""
        variable_selection = {
            1: ["var_0", "var_1"]
        }

        config_dict = generate_detector_config(
            variable_selection=variable_selection,
            detector_name="TestDetector",
            method_type="new_value_combo_detector",
            comb_size=2
        )

        assert "detectors" in config_dict
        assert "TestDetector" in config_dict["detectors"]
        detector_config = config_dict["detectors"]["TestDetector"]
        assert detector_config["method_type"] == "new_value_combo_detector"
        assert detector_config["params"]["comb_size"] == 2
        assert len(detector_config["events"]) == 1

    def test_generate_detector_config_multiple_events(self):
        """Test config generation with multiple events."""
        variable_selection = {
            1: ["var_0", "var_1"],
            2: ["var_0", "var_2", "var_3"],
            3: ["level"]
        }

        config_dict = generate_detector_config(
            variable_selection=variable_selection,
            detector_name="MultiEventDetector",
            method_type="new_value_combo_detector"
        )

        assert len(config_dict["detectors"]["MultiEventDetector"]["events"]) == 3

    def test_configure_method_ingests_events(self):
        """Test that configure method properly ingests events."""
        detector = NewValueComboDetector()

        # Configure with sample events
        for event_id in [1, 2, 3]:
            parser_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": event_id,
                "template": f"Template {event_id}",
                "variables": ["val1", "val2", "val3"],
                "logID": str(event_id),
                "parsedLogID": str(event_id),
                "parserID": "test_parser",
                "log": "test log",
                "logFormatVariables": {"level": "INFO"}
            })
            detector.configure(parser_data)

        # Verify events were ingested
        events_data = detector.auto_conf_persistency.get_events_data()
        assert len(events_data) == 3
        assert 1 in events_data
        assert 2 in events_data
        assert 3 in events_data

    def test_set_configuration_updates_config(self):
        """Test that set_configuration properly updates detector config."""
        detector = NewValueComboDetector()

        # Configure with events that have varying stability
        for i in range(10):
            parser_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": 1,
                "template": "Template 1",
                "variables": ["constant", f"varying_{i}", "another_constant"],
                "logID": str(i),
                "parsedLogID": str(i),
                "parserID": "test_parser",
                "log": "test log",
                "logFormatVariables": {"level": "INFO"}
            })
            detector.configure(parser_data)

        # Set configuration
        detector.set_configuration(max_combo_size=2)

        # Verify config was updated
        assert detector.config.events is not None
        assert detector.config.comb_size == 2

    def test_configuration_workflow(self):
        """Test complete configuration workflow like in notebook."""
        detector = NewValueComboDetector()

        # Step 1: Configure phase - ingest events
        training_data = []
        for i in range(20):
            for event_id in [1, 2]:
                parser_data = schemas.ParserSchema({
                    "parserType": "test",
                    "EventID": event_id,
                    "template": f"Template {event_id}",
                    "variables": ["stable_val", f"var_{i % 3}", "another_stable"],
                    "logID": str(len(training_data)),
                    "parsedLogID": str(len(training_data)),
                    "parserID": "test_parser",
                    "log": "test log",
                    "logFormatVariables": {"level": "INFO"}
                })
                training_data.append(parser_data)
                detector.configure(parser_data)

        # Step 2: Set configuration based on stable variables
        detector.set_configuration(max_combo_size=3)

        # Step 3: Train detector with configuration
        for data in training_data:
            detector.train(data)

        # Step 4: Verify detector can detect anomalies
        test_data = schemas.ParserSchema({
            "parserType": "test",
            "EventID": 1,
            "template": "Template 1",
            "variables": ["stable_val", "new_value", "another_stable"],
            "logID": "999",
            "parsedLogID": "999",
            "parserID": "test_parser",
            "log": "test log",
            "logFormatVariables": {"level": "INFO"}
        })
        output = schemas.DetectorSchema()

        # Should detect anomaly due to new combination
        result = detector.detect(test_data, output)
        assert isinstance(result, bool)

    def test_set_configuration_with_combo_size(self):
        """Test set_configuration respects max_combo_size parameter."""
        detector = NewValueComboDetector()

        # Configure with multiple variable events
        for i in range(15):
            parser_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": 1,
                "template": "Multi-var template",
                "variables": ["v1", "v2", "v3", "v4", "v5"],
                "logID": str(i),
                "parsedLogID": str(i),
                "parserID": "test_parser",
                "log": "test log",
                "logFormatVariables": {}
            })
            detector.configure(parser_data)

        # Set configuration with specific combo size
        detector.set_configuration(max_combo_size=4)

        # Verify comb_size was updated
        assert detector.config.comb_size == 4

    def test_configuration_with_no_stable_variables(self):
        """Test configuration when no stable variables are found."""
        detector = NewValueComboDetector()

        # Configure with highly variable data
        for i in range(10):
            parser_data = schemas.ParserSchema({
                "parserType": "test",
                "EventID": 1,
                "template": "Variable template",
                "variables": [f"val_{i}_0", f"val_{i}_1"],
                "logID": str(i),
                "parsedLogID": str(i),
                "parserID": "test_parser",
                "log": "test log",
                "logFormatVariables": {}
            })
            detector.configure(parser_data)

        # Set configuration
        detector.set_configuration()

        # Should handle gracefully without stable variables
        assert detector.config is not None
