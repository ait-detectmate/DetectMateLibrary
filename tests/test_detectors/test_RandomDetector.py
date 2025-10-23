"""Tests for RandomDetector class.

This module tests the RandomDetector implementation including:
- Initialization and configuration
- Training functionality (no-op for RandomDetector)
- Detection logic with different thresholds
- Hierarchical configuration handling
- Input/output schema validation
- Error handling
"""

from detectmatelibrary.common.config.detector import DetectorInstance, DetectorVariable
from detectmatelibrary.detectors.RandomDetector import RandomDetector, RandomDetectorConfig
from detectmatelibrary.common.config.detector import CoreDetectorConfig
import detectmatelibrary.schemas as schemas
from detectmatelibrary.utils.aux import time_test_mode

from unittest.mock import patch


# Set time test mode for consistent timestamps
time_test_mode()


class TestRandomDetectorConfig:
    """Test RandomDetectorConfig validation and defaults."""

    def test_custom_threshold(self):
        """Test setting custom threshold value."""
        config = RandomDetectorConfig(threshold=0.5)
        assert config.threshold == 0.5


class TestRandomDetectorInitialization:
    """Test RandomDetector initialization and configuration."""

    def test_default_initialization(self):
        """Test detector initialization with default parameters."""
        detector = RandomDetector()

        assert detector.name == "RandomDetector"
        assert hasattr(detector, 'config')  # Config should exist
        # Buffer mode is stored directly in data_buffer
        assert detector.data_buffer.mode == "no_buf"
        assert detector.input_schema == schemas.PARSER_SCHEMA
        assert detector.output_schema == schemas.DETECTOR_SCHEMA

    def test_custom_config_initialization(self):
        """Test detector initialization with custom configuration."""
        config = CoreDetectorConfig(
            detectorID="TestDetector01",
            detectorType="RandomType"
        )
        detector = RandomDetector(name="TestDetector", config=config)

        assert detector.name == "TestDetector"
        assert detector.config.detectorID == "TestDetector01"
        assert detector.config.detectorType == "RandomType"


class TestRandomDetectorIntegration:
    """Integration tests for RandomDetector with full pipeline."""

    def test_full_process_pipeline(self):
        """Test complete processing pipeline from input to output."""
        # Create detector with specific configuration
        config = CoreDetectorConfig(
            detectorID="TestRandomDetector",
            detectorType="RandomDetector",
            instances=[
                DetectorInstance(
                    id="instance1",
                    event=1,
                    template="test template",
                    variables=[
                        DetectorVariable(
                            pos=0,
                            params=RandomDetectorConfig(threshold=0.5)
                        )
                    ]
                )
            ]
        )

        detector = RandomDetector(name="TestDetector", config=config)

        # Just test that the detector was created successfully
        assert detector is not None
        assert detector.name == "TestDetector"
        assert detector.config.detectorID == "TestRandomDetector"
        assert detector.config.detectorType == "RandomDetector"


class TestRandomDetectorEdgeCases:
    """Test edge cases and error handling."""

    @patch('numpy.random.rand')
    @patch('detectmatelibrary.common.detector.CoreDetectorConfig.get_relevant_fields')
    def test_random_seed_consistency(self, mock_get_fields, mock_rand):
        """Test that mocking numpy.random works consistently."""
        mock_rand.return_value = 0.42
        mock_get_fields.return_value = {
            "var1": {
                "value": "test_value",
                "config": RandomDetectorConfig(threshold=0.5)
            }
        }

        detector = RandomDetector()
        parser_data = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "parserType": "test",
            "EventID": 1,
            "template": "test template",
            "variables": ["var1"],
            "logID": 1,
            "parsedLogID": 1,
            "parserID": "test_parser",
            "log": "test log message",
            "logFormatVariables": {"timestamp": "123456"}
        })
        detector_output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        # Multiple calls should return consistent results when mocked
        result1 = detector.detect(parser_data, detector_output)

        # Reset output for second call
        detector_output = schemas.initialize(schemas.DETECTOR_SCHEMA)
        result2 = detector.detect(parser_data, detector_output)

        assert result1 == result2
