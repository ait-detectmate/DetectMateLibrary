"""The auto_config_params block: parsing, round-trip, and strictness."""

import warnings

import pytest
from pydantic import ValidationError

from detectmatelibrary.common._config import AutoConfigParams, BasicConfig
from detectmatelibrary.common._config._compile import MissingParamsWarning
from detectmatelibrary.common.alert_aggregator import CoreAlertAggregatorConfig
from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.parser import CoreParserConfig

CONFIG_CLASSES = (CoreParserConfig, CoreDetectorConfig, CoreAlertAggregatorConfig)


class _Params(AutoConfigParams):
    knob: int = 1


class _Config(CoreDetectorConfig):
    method_type: str = "test_detector"
    auto_config_params: _Params = _Params()


def _wrap(entry: dict) -> dict:
    return {"detectors": {"TestDetector": entry}}


def _from_dict(**entry: object) -> _Config:
    return _Config.from_dict(
        _wrap({"method_type": "test_detector", "auto_config": True, **entry}),
        "TestDetector",
    )


def test_block_round_trips():
    """YAML -> pydantic -> YAML, staying out of the operational params
    block."""
    cfg = _from_dict(auto_config_params={"knob": 7})
    assert cfg.auto_config_params.knob == 7

    dumped = cfg.to_dict(method_id="TestDetector")["detectors"]["TestDetector"]
    assert dumped["auto_config_params"] == {"knob": 7}
    assert "knob" not in dumped.get("params", {})


def test_default_block_is_not_emitted():
    """A config that never touches auto-config serializes exactly as before.

    Also covers the component types that inherit the block empty: adding it
    to the shared base must not add a key to anyone's YAML.
    """
    dumped = _Config().to_dict(method_id="TestDetector")["detectors"]["TestDetector"]
    assert "auto_config_params" not in dumped

    for config_cls in CONFIG_CLASSES:
        config = config_cls()
        dumped = config.to_dict(method_id="M")[config.component_type]["M"]
        assert "auto_config_params" not in dumped


def test_unknown_key_in_block_is_rejected():
    """Extra='forbid' reaches every component type, including those that
    declare no fields in the block."""
    with pytest.raises(ValidationError):
        _from_dict(auto_config_params={"nope": 1})

    for config_cls in CONFIG_CLASSES:
        with pytest.raises(ValidationError):
            config_cls(auto_config_params={"nope": 1})


def test_auto_param_under_params_is_rejected():
    """The clean break: the old flat spelling is an error, not a silent no-
    op."""
    with pytest.raises(ValidationError):
        _from_dict(params={"knob": 7})


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


def test_block_is_declared_on_the_shared_base():
    """Not detector-only: the block sits beside `auto_config` on BasicConfig,
    since `auto_config` and `Component.configure()` are both declared there."""
    assert "auto_config_params" in BasicConfig.model_fields
    for config_cls in CONFIG_CLASSES:
        assert isinstance(config_cls().auto_config_params, AutoConfigParams)
