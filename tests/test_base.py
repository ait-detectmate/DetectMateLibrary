from src.schemas import NotSupportedSchema, initialize, ANY_SCHEMA, serialize
from src.components.Base.ComponentBase import ConfigBase, ComponentBase

import pydantic
import pytest


class DummyConfig(ConfigBase):
    thresholds: float = 0.7
    max_iter: int = 50


class DummyComponent(ComponentBase):
    def __init__(self, name: str, config: DummyConfig = DummyConfig()) -> None:
        super().__init__(name=name, type_="Dummy", config=config)


class DummyComponentWithBuffer(ComponentBase):
    def __init__(self, name: str, config: DummyConfig = DummyConfig()) -> None:
        super().__init__(
            name=name,
            type_="DummyWithBuffer",
            config=config,
            buffer_mode="batch",
            buffer_size=3,
            process_function=sum
        )


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


class TestComponentBase:
    def test_initalize_empty(self) -> None:
        component = ComponentBase(name="TestComponent")

        assert component.name == "TestComponent"
        assert component.type_ == "Base"
        assert isinstance(component.config, ConfigBase)
        assert component.config.get_config() == {}

    def test_initalize_with_config(self) -> None:
        config = DummyConfig(thresholds=0.6, max_iter=80)
        component = DummyComponent(name="Dummy1", config=config)

        assert component.name == "Dummy1"
        assert component.type_ == "Dummy"
        assert isinstance(component.config, DummyConfig)
        assert component.config.get_config() == {"thresholds": 0.6, "max_iter": 80}

    def test_process_no_buffer(self) -> None:
        component = DummyComponent(name="Dummy2", config=DummyConfig())
        result = component.process(42)

        assert result == 42

    def test_process_with_buffer(self) -> None:
        component = DummyComponentWithBuffer(name="DummyWithBuf", config=DummyConfig())

        assert component.process(1) is None
        assert component.process(2) is None
        assert component.process(3) == 6

    def test_process_byte_input(self) -> None:
        component = DummyComponent(name="Dummy5", config=DummyConfig())

        data = serialize(ANY_SCHEMA, initialize(ANY_SCHEMA, **{"__version__": "1.0.0"}))
        output = component.process(data)

        assert data == output

    def test_process_invalid_schema(self) -> None:
        component = DummyComponent(name="Dummy4", config=DummyConfig())

        with pytest.raises(NotSupportedSchema):
            component.process(b"invalid bytes")

    def test_update_config(self) -> None:
        component = DummyComponent(name="Dummy3", config=DummyConfig())

        assert component.get_config() == {"thresholds": 0.7, "max_iter": 50}
        component.update_config({"thresholds": 0.95})
        assert component.get_config() == {"thresholds": 0.95, "max_iter": 50}
