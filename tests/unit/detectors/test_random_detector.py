"""Tests for detectmatelibrary.detectors.random_detector."""
from detectmatelibrary.detectors.random_detector import RandomDetector
import detectmatelibrary.schemas as sc
import pytest

from copy import deepcopy

pytestmark = pytest.mark.usefixtures("frozen_timestamps")

config = {
    "detectors": {
        "TestDetector": {
            "auto_config": False,
            "method_type": "random_detector",
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 0,
                            "name": "process",
                            "params": {
                                "threshold": 0.
                            }
                        }]
                    }
                }
            }
        }
    }
}


class TestRandomDetectorEdgeCases:
    """Test edge cases and error handling."""

    def test_random_seed_consistency(self):

        detector = RandomDetector(name="TestDetector", config=deepcopy(config))
        parser_data = sc.ParserSchema({
            "parserType": "test",
            "eventID": 1,
            "template": "test template",
            "variables": ["var1"],
            "logID": "1",
            "parsedLogID": "1",
            "parserID": "test_parser",
            "log": "test log message",
            "headerVariables": {"timestamp": "123456"}
        })
        detector_output = sc.DetectorSchema()

        # Multiple calls should return consistent results when mocked
        result1 = detector.detect(parser_data, detector_output)

        # Reset output for second call
        detector_output = sc.DetectorSchema()
        result2 = detector.detect(parser_data, detector_output)

        assert result1 == result2
