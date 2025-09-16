import pytest
from src.components.Base.ConfigBase import ConfigBase
import pydantic


class DummyConfig(ConfigBase):
    thresholds: float = 0.7
    max_iter: int = 50


class TestConfigBase:
    def test_initialize(self) -> None:
        config = DummyConfig(thresholds=0.5, max_iter=100)

        assert isinstance(config, ConfigBase)
        assert config.get_config() == {"thresholds": 0.5, "max_iter": 100}

    def test_incorect_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            DummyConfig(thresholds="high", max_iter="many")

    def test_update_config(self) -> None:
        config = DummyConfig()
        assert config.get_config() == {"thresholds": 0.7, "max_iter": 50}

        config.update_config({"thresholds": 0.9})
        assert config.get_config() == {"thresholds": 0.9, "max_iter": 50}

        config.update_config({"max_iter": 200})
        assert config.get_config() == {"thresholds": 0.9, "max_iter": 200}

    def test_add_new_parameter(self) -> None:
        config = DummyConfig()
        with pytest.raises(ValueError):
            config.update_config({"new_param": 123})

    def test_add_new_parameter_initialization(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            DummyConfig(new_param=123)
