"""Tests for detectmatelibrary.base_detectors.variable_detector."""
from detectmatelibrary.base_detectors import VariableDetector
import detectmatelibrary.schemas as sc

import pytest
from pydantic import ValidationError
from detectmatelibrary.base_detectors import VariableAutoConfigParams


CONFIG = {
    "detectors": {
        "detector": {
            "method_type": "variable_detector",
            "auto_config": False,
            "params": {
                "allow_fed": True,
            },
            "events": {
                1: {
                    "i": {
                        "params": {},
                        "variables": [{"pos": 0, "name": "user", "params": {}}]
                    }
                }
            },
        }
    }
}


def train(detector: VariableDetector, *users) -> None:
    for u in users:
        detector.train(sc.ParserSchema({
            "parserType": "t", "eventID": 1, "template": "t", "variables": [u],
            "logID": "1", "parsedLogID": "1", "parserID": "p", "log": "l",
            "headerVariables": {},
        }))


class TestFederation:
    def test_train(self):
        detector1 = VariableDetector(name="detector", config=CONFIG)
        train(detector1, "A", "B", "C")

        users = detector1.persistency.get_event_data(1)["user"].unique_set
        assert {"A", "B", "C"} == users
        assert len(detector1.persistency.event_struct.get_data()) == 3


class TestOldConfigFieldsAreRejected:
    """Clean break: AutoConfigParams sets extra='forbid', so the old
    spellings raise instead of being silently ignored."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"segmentation": "both"},
            {"require_declining": True},
            {"incline_threshold": -0.25},
        ],
    )
    def test_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            VariableAutoConfigParams(**kwargs)
