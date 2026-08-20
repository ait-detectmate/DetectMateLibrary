"""The auto_config_params block: parsing, round-trip, and strictness."""

import warnings

import pytest
from pydantic import ValidationError

from detectmatelibrary.common._config._compile import MissingParamsWarning
from detectmatelibrary.common.detector import AutoConfigParams, CoreDetectorConfig


class _Params(AutoConfigParams):
    knob: int = 1


class _Config(CoreDetectorConfig):
    method_type: str = "test_detector"
    auto_config_params: _Params = _Params()


def _wrap(entry: dict) -> dict:
    return {"detectors": {"TestDetector": entry}}


def test_block_is_parsed_into_the_nested_model():
    cfg = _Config.from_dict(
        _wrap({
            "method_type": "test_detector",
            "auto_config": True,
            "auto_config_params": {"knob": 7},
        }),
        "TestDetector",
    )
    assert cfg.auto_config_params.knob == 7


def test_block_round_trips():
    cfg = _Config.from_dict(
        _wrap({
            "method_type": "test_detector",
            "auto_config": True,
            "auto_config_params": {"knob": 7},
        }),
        "TestDetector",
    )
    dumped = cfg.to_dict(method_id="TestDetector")["detectors"]["TestDetector"]
    assert dumped["auto_config_params"] == {"knob": 7}
    assert "knob" not in dumped.get("params", {})


def test_default_block_is_not_emitted():
    """A config that never touches auto-config serializes exactly as before."""
    dumped = _Config().to_dict(method_id="TestDetector")["detectors"]["TestDetector"]
    assert "auto_config_params" not in dumped


def test_unknown_key_in_block_is_rejected():
    with pytest.raises(ValidationError):
        _Config.from_dict(
            _wrap({
                "method_type": "test_detector",
                "auto_config": True,
                "auto_config_params": {"nope": 1},
            }),
            "TestDetector",
        )


def test_auto_param_under_params_is_rejected():
    """The clean break: the old flat spelling is an error, not a silent no-op."""
    with pytest.raises(ValidationError):
        _Config.from_dict(
            _wrap({
                "method_type": "test_detector",
                "auto_config": True,
                "params": {"knob": 7},
            }),
            "TestDetector",
        )


def test_block_alone_counts_as_data():
    """auto_config_params is real configuration and must not trip
    MissingParamsWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", MissingParamsWarning)
        _Config.from_dict(
            _wrap({
                "method_type": "test_detector",
                "auto_config": False,
                "auto_config_params": {"knob": 7},
            }),
            "TestDetector",
        )
