from detectmatelibrary.detectors.random_detector import RandomDetector
import detectmatelibrary.schemas as schemas
from detectmatelibrary.utils.aux import time_test_mode


time_test_mode()


class TestRandomDetectorIntegration:
    """Integration tests for RandomDetector with full pipeline."""

    def test_full_process_pipeline(self):
        config = {
            "detectors": {
                "TestDetector": {
                    "auto_config": False,
                    "method_type": "random_detector",
                    "params": {
                        "log_variables": [{
                            "id": "test",
                            "event": 1,
                            "template": "dummy template",
                            "variables": [{
                                "pos": 0,
                                "name": "process",
                                "params": {
                                    "threshold": 0.5
                                }
                            }]
                        }]
                    }
                }
            }
        }

        detector = RandomDetector(name="TestDetector", config=config)

        assert detector is not None
        assert detector.name == "TestDetector"
        assert detector.config.log_variables[1].variables[0].name == "process"


class TestRandomDetectorEdgeCases:
    """Test edge cases and error handling."""

    def test_random_seed_consistency(self):
        config = {
            "detectors": {
                "TestDetector": {
                    "auto_config": False,
                    "method_type": "random_detector",
                    "params": {
                        "log_variables": [{
                            "id": "test",
                            "event": 1,
                            "template": "dummy template",
                            "variables": [{
                                "pos": 0,
                                "name": "process",
                                "params": {
                                    "threshold": 0.0
                                }
                            }]
                        }]
                    }
                }
            }
        }

        detector = RandomDetector(name="TestDetector", config=config)
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
