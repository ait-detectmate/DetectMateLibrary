from src.components.utils.aux import BasicConfig
from src.components.common.core import CoreConfig, CoreComponent
from src.components.utils.data_buffer import ArgsBuffer
import src.schemas as schemas

import pydantic
import pytest


class MockConfig(CoreConfig):
    thresholds: float = 0.7
    max_iter: int = 50


class MockComponent(CoreComponent):
    def __init__(self, name: str, config: MockConfig = MockConfig()) -> None:
        super().__init__(name=name, type_="Dummy", config=config)


class DummyComponentWithBuffer(CoreComponent):
    def __init__(self, name: str, config: MockConfig = MockConfig()) -> None:
        super().__init__(
            name=name,
            config=config,
            type_="DummyWithBuffer",
            args_buffer=ArgsBuffer(mode="batch", size=3, process_function=sum),
        )


class TestConfigCore:
    def test_initialize(self) -> None:
        config = MockConfig(thresholds=0.5, max_iter=100)

        assert isinstance(config, BasicConfig)
        assert config.get_config() == {"thresholds": 0.5, "max_iter": 100, "start_id": 0}

    def test_initialize_dict(self) -> None:
        config = MockConfig.from_dict({"thresholds": 0.8, "max_iter": 30, "start_id": 0})

        assert isinstance(config, BasicConfig)
        assert config.get_config() == {"thresholds": 0.8, "max_iter": 30, "start_id": 0}

    def test_incorect_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockConfig(thresholds="high", max_iter="many")

    def test_update_config(self) -> None:
        config = MockConfig()
        assert config.get_config() == {"thresholds": 0.7, "max_iter": 50, "start_id": 0}

        config.update_config({"thresholds": 0.9})
        assert config.get_config() == {"thresholds": 0.9, "max_iter": 50, "start_id": 0}

        config.update_config({"max_iter": 200})
        assert config.get_config() == {"thresholds": 0.9, "max_iter": 200, "start_id": 0}

    def test_add_new_parameter(self) -> None:
        config = MockConfig()
        with pytest.raises(ValueError):
            config.update_config({"new_param": 123})

    def test_add_new_parameter_initialization(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockConfig(new_param=123)


class TestCoreComponent:
    def test_initalize_empty(self) -> None:
        component = CoreComponent(name="TestComponent")

        assert component.name == "TestComponent"
        assert component.type_ == "Core"
        assert isinstance(component.config, CoreConfig)
        assert component.config.get_config() == {"start_id": 0}

    def test_initalize_with_config(self) -> None:
        config = MockConfig(thresholds=0.6, max_iter=80)
        component = MockComponent(name="Dummy1", config=config)

        assert component.name == "Dummy1"
        assert component.type_ == "Dummy"
        assert isinstance(component.config, MockConfig)
        assert component.config.get_config() == {"thresholds": 0.6, "max_iter": 80, "start_id": 0}

    def test_process_no_buffer(self) -> None:
        component = MockComponent(name="Dummy2", config=MockConfig())
        result = component.process(42)

        assert result == 42

    def test_process_with_buffer(self) -> None:
        component = DummyComponentWithBuffer(name="DummyWithBuf", config=MockConfig())

        assert component.process(1) is None
        assert component.process(2) is None
        assert component.process(3) == 6

    def test_process_byte_input(self) -> None:
        component = MockComponent(name="Dummy5", config=MockConfig())

        data = schemas.serialize(
            schemas.BASE_SCHEMA,
            schemas.initialize(schemas.BASE_SCHEMA, **{"__version__": "1.0.0"})
        )
        output = component.process(data)

        assert data == output

    def test_process_invalid_schema(self) -> None:
        component = MockComponent(name="Dummy4", config=MockConfig())

        with pytest.raises(schemas.NotSupportedSchema):
            component.process(b"invalid bytes")

    def test_update_config(self) -> None:
        component = MockComponent(name="Dummy3", config=MockConfig())

        assert component.get_config() == {
            "thresholds": 0.7, "max_iter": 50, "start_id": 0
        }
        component.update_config({"thresholds": 0.95})
        assert component.get_config() == {
            "thresholds": 0.95, "max_iter": 50, "start_id": 0
        }
