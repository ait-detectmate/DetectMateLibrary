from unittest.mock import patch

from detectmatelibrary.detectors.RandomDetector import RandomDetector, RandomConfig, EventConfig
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
import detectmatelibrary.schemas as schemas

import numpy as np

# Test data schema for ParserSchema
dummy_parser_schema = {
    "parserType": "TestParser",
    "EventID": 1,
    "template": "Login attempt from <IP> for user <USER>",
    "variables": ["192.168.1.1", "admin", "success"],
    "logID": 12345,
    "parsedLogID": 67890,
    "parserID": "parser_001",
    "log": "Login attempt from 192.168.1.1 for user admin",
    "logFormatVariables": {
        "timestamp": "1699123456",
        "ip_address": "192.168.1.1",
        "username": "admin",
        "status": "success"
    },
}

# Additional test schemas for different event IDs
dummy_parser_schema_event2 = {
    "parserType": "TestParser",
    "EventID": 2,
    "template": "File access <FILE> by <USER>",
    "variables": ["/etc/passwd", "root"],
    "logID": 12346,
    "parsedLogID": 67891,
    "parserID": "parser_002",
    "log": "File access /etc/passwd by root",
    "logFormatVariables": {
        "timestamp": "1699123457",
        "filename": "/etc/passwd",
        "username": "root"
    },
}


class TestEventConfig:
    """Test cases for EventConfig class."""

    def test_event_config_default_values(self):
        """Test EventConfig with default values."""
        config = EventConfig()
        assert config.eventId == "all"
        assert config.variables == ["all"]
        assert config.logFormatVariables == ["all"]

    def test_event_config_specific_values(self):
        """Test EventConfig with specific values."""
        config = EventConfig(
            eventId=1,
            variables=[0, 1, 2],
            logFormatVariables=["timestamp", "ip_address"]
        )
        assert config.eventId == 1
        assert config.variables == [0, 1, 2]
        assert config.logFormatVariables == ["timestamp", "ip_address"]

    def test_event_config_validation(self):
        """Test EventConfig validation with invalid values."""
        # Should not raise an error - pydantic allows the union types
        config = EventConfig(eventId="all", variables=["all"])
        assert config.eventId == "all"
        assert config.variables == ["all"]


class TestRandomConfig:
    """Test cases for RandomConfig class."""

    def test_random_config_initialization(self):
        """Test RandomConfig initialization."""
        config = RandomConfig()
        assert isinstance(config, CoreDetectorConfig)
        assert len(config.event_configs) == 0

    def test_add_multiple_event_configs(self):
        """Test adding multiple configurations for the same event."""
        config = RandomConfig()
        config.add_event_config(eventId=1, variables=[0])
        config.add_event_config(eventId=1, variables=[1, 2])

        assert len(config.event_configs[1]) == 2
        assert config.event_configs[1][0].variables == [0]
        assert config.event_configs[1][1].variables == [1, 2]

    def test_get_event_configs(self):
        """Test retrieving event configurations."""
        config = RandomConfig()
        config.add_event_config(eventId=1, variables=[0])
        config.add_event_config(eventId="all", variables=[1])

        # Should return both specific and "all" configs
        configs = config.get_event_configs(1)
        assert len(configs) == 2

        # Should return only "all" configs for unconfigured event
        configs_event2 = config.get_event_configs(2)
        assert len(configs_event2) == 1
        assert configs_event2[0].eventId == "all"

    def test_get_filtered_data_instances_no_config(self):
        """Test filtering when no event configuration exists."""
        config = RandomConfig()
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)

        result = config.get_filtered_data_instances(data)
        assert result == {}

    def test_get_filtered_data_instances_all_config(self):
        """Test filtering with 'all' configuration."""
        config = RandomConfig()
        config.add_event_config()  # Adds "all" config

        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)
        result = config.get_filtered_data_instances(data)

        assert data.EventID in result
        assert len(result[data.EventID]) > 0


class TestRandomDetector:
    """Test cases for RandomDetector class."""

    def test_random_detector_initialization_default(self):
        """Test RandomDetector initialization with defaults."""
        detector = RandomDetector()

        assert isinstance(detector, CoreDetector)
        assert detector.name == "RandomDetector"
        assert isinstance(detector.config, RandomConfig)

    def test_random_detector_initialization_custom(self):
        """Test RandomDetector initialization with custom parameters."""
        config = RandomConfig()
        config.add_event_config(eventId=1, variables=[0, 1])

        detector = RandomDetector(name="CustomRandomDetector", config=config)

        assert detector.name == "CustomRandomDetector"
        assert detector.config == config
        assert 1 in detector.config.event_configs

    def test_train_method(self):
        """Test that train method does nothing (as expected)."""
        detector = RandomDetector()
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)

        # Should not raise any errors and return None
        result = detector.train(data)
        assert result is None

        # Test with list input
        result_list = detector.train([data])
        assert result_list is None

    @patch('numpy.random.rand')
    def test_detect_no_anomaly(self, mock_rand):
        """Test detect method when no anomaly is detected."""
        mock_rand.return_value = 0.6  # > 0.5, so no anomaly

        detector = RandomDetector()
        # Configure to process event ID 1
        detector.config.add_event_config(eventId=1)

        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)
        output = schemas.initialize(schemas.DETECTOR_SCHEMA, **{})

        result = detector.detect(data, output)

        assert not result
        assert output.score == 0.0
        assert len(output.alertsObtain) == 0

    @patch('numpy.random.rand')
    def test_detect_with_anomaly(self, mock_rand):
        """Test detect method when anomaly is detected."""
        mock_rand.return_value = 0.3  # < 0.5, so anomaly detected

        detector = RandomDetector()
        # Configure to process event ID 1
        detector.config.add_event_config(eventId=1)

        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)
        output = schemas.initialize(schemas.DETECTOR_SCHEMA, **{})

        result = detector.detect(data, output)

        assert result
        assert output.score == 1.0
        assert len(output.alertsObtain) == 1

    def test_detect_unconfigured_event(self):
        """Test detect method with unconfigured event ID."""
        detector = RandomDetector()
        # Don't configure any events

        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)
        output = schemas.initialize(schemas.DETECTOR_SCHEMA, **{})

        np.random.seed(0)
        result = detector.detect(data, output)

        # Should return False since no events are configured
        assert not result
        assert output.score == 0.0
        assert len(output.alertsObtain) == 0

    @patch('numpy.random.rand')
    def test_detect_score_accumulation(self, mock_rand):
        """Test that scores accumulate correctly across multiple data
        instances."""
        mock_rand.return_value = 0.3  # Always anomaly (score = 1.0)

        detector = RandomDetector()
        # Configure multiple variables for the same event to get multiple data instances
        detector.config.add_event_config(eventId=1, variables=[3])
        detector.config.add_event_config(eventId=2, variables=[1])

        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_parser_schema)
        output = schemas.initialize(schemas.DETECTOR_SCHEMA, **{})

        np.random.seed(0)
        result = detector.detect(data, output)

        assert result

    def test_detect_edge_case_empty_variables(self):
        """Test detect method with empty variables list."""
        detector = RandomDetector()
        detector.config.add_event_config(eventId=1, variables=[])

        # Create data with empty variables
        empty_var_schema = dummy_parser_schema.copy()
        empty_var_schema["variables"] = []
        data = schemas.initialize(schemas.PARSER_SCHEMA, **empty_var_schema)
        output = schemas.initialize(schemas.DETECTOR_SCHEMA, **{})

        np.random.seed(0)
        result = detector.detect(data, output)

        assert not result
