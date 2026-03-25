from detectmatelibrary.common._core_op._fit_logic import ConfigState, TrainState
from detectmatelibrary.common.core import CoreConfig, CoreComponent
from detectmatelibrary.common._config import BasicConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer

import detectmatelibrary.schemas._op as op_schemas
import detectmatelibrary.schemas as schemas

import pydantic
import pytest


class MockConfig(CoreConfig):
    thresholds: float = 0.7
    max_iter: int = 50


class MockConfigWithTraining(CoreConfig):
    thresholds: float = 0.7
    max_iter: int = 50

    data_use_training: int | None = 4


default_args = {
    "method_type": "default_method_type",
    "component_type": "default_type",
    "auto_config": False,
    "start_id": 10,
    "data_use_training": None,
    "data_use_configure": None
}


class MockComponent(CoreComponent):
    def __init__(self, name: str, config: MockConfig = MockConfig()) -> None:
        super().__init__(name=name, type_="Dummy", config=config)


class MockComponentWithTraining(CoreComponent):
    def __init__(
        self, name: str, config: MockConfigWithTraining = MockConfigWithTraining()
    ) -> None:
        super().__init__(
            name=name, type_="Dummy", config=config, input_schema=schemas.LogSchema
        )
        self.train_data = []

    def train(self, input_) -> None:
        self.train_data.append(input_)

    def run(self, input_, output_) -> None:
        return False


class MockConfigWithConfigure(CoreConfig):
    thresholds: float = 0.7
    max_iter: int = 50
    data_use_configure: int | None = 3


class MockComponentWithConfigure(CoreComponent):
    def __init__(
        self, name: str, config: MockConfigWithConfigure = MockConfigWithConfigure()
    ) -> None:
        super().__init__(
            name=name, type_="Dummy", config=config, input_schema=schemas.LogSchema
        )
        self.configure_data: list = []
        self.set_configuration_called: int = 0

    def configure(self, input_) -> None:
        self.configure_data.append(input_)

    def set_configuration(self) -> None:
        self.set_configuration_called += 1

    def run(self, input_, output_) -> bool:
        return False


class MockComponentWithConfigureAndTraining(CoreComponent):
    def __init__(self, name: str, config: CoreConfig = CoreConfig()) -> None:
        super().__init__(
            name=name, type_="Dummy", config=config, input_schema=schemas.LogSchema
        )
        self.configure_data: list = []
        self.train_data: list = []
        self.set_configuration_called: int = 0

    def configure(self, input_) -> None:
        self.configure_data.append(input_)

    def set_configuration(self) -> None:
        self.set_configuration_called += 1

    def train(self, input_) -> None:
        self.train_data.append(input_)

    def run(self, input_, output_) -> bool:
        return False


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
        expected = {"thresholds": 0.5, "max_iter": 100}
        expected.update(default_args)

        assert isinstance(config, BasicConfig)
        assert config.get_config() == expected

    def test_initialize_dict(self) -> None:
        config = MockConfig.from_dict(
            {
                "default_type": {
                    "test_id": {
                        "method_type": "default_method_type",
                        "auto_config": False,
                        "data_use_training": 10,
                        "params": {"thresholds": 0.8, "max_iter": 30, "start_id": 10}
                    }
                }
            },
            "test_id"
        )
        expected = {"thresholds": 0.8, "max_iter": 30}
        expected.update(default_args)
        expected["data_use_training"] = 10

        assert isinstance(config, BasicConfig)
        assert config.get_config() == expected

    def test_incorect_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockConfig(thresholds="high", max_iter="many")

    def test_update_config(self) -> None:
        config = MockConfig()

        expected = {"thresholds": 0.7, "max_iter": 50, "data_use_training": None}
        expected.update(default_args)
        assert config.get_config() == expected

        expected = {"thresholds": 0.9, "max_iter": 50, "data_use_training": None}
        expected.update(default_args)
        config.update_config({"thresholds": 0.9})
        assert config.get_config() == expected

        expected = {"max_iter": 200, "thresholds": 0.9, "data_use_training": None}
        expected.update(default_args)
        config.update_config({"max_iter": 200})
        assert config.get_config() == expected

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
        assert component.config.get_config() == default_args

    def test_initalize_with_config(self) -> None:
        config = MockConfig(thresholds=0.6, max_iter=80)
        component = MockComponent(name="Dummy1", config=config)
        expected = {"max_iter": 80, "thresholds": 0.6}
        expected.update(default_args)

        assert component.name == "Dummy1"
        assert component.type_ == "Dummy"
        assert isinstance(component.config, MockConfig)
        assert component.config.get_config() == expected

    def test_process_invalid_schema(self) -> None:
        component = MockComponent(name="Dummy4", config=MockConfig())

        with pytest.raises(op_schemas.NotSupportedSchema):
            component.process(b"invalid bytes")

    def test_update_config(self) -> None:
        component = MockComponent(name="Dummy3", config=MockConfig())

        expected = {"max_iter": 50, "thresholds": 0.7}
        expected.update(default_args)
        assert component.get_config() == expected
        component.update_config({"thresholds": 0.95})

        expected = {"max_iter": 50, "thresholds": 0.95}
        expected.update(default_args)
        assert component.get_config() == expected

    def test_training(self) -> None:
        component = MockComponentWithTraining(name="Dummy4")

        for i in range(10):
            component.process(
                schemas.LogSchema({
                    "__version__": "1.0.0",
                    "logID": str(i),
                    "logSource": "test",
                    "hostname": "test_hostname"
                })
            )

        assert len(component.train_data) == component.fitlogic.data_used_train
        for i, log in enumerate(component.train_data):
            expected = schemas.LogSchema({
                "__version__": "1.0.0",
                "logID": str(i),
                "logSource": "test",
                "hostname": "test_hostname"
            })
            assert expected == log

    def test_training_force_stop(self) -> None:
        component = MockComponentWithTraining(name="Dummy5")

        for i in range(10):
            if i == 2:
                component.fitlogic.train_state = TrainState.STOP_TRAINING
            component.process(
                schemas.LogSchema({
                    "__version__": "1.0.0",
                    "logID": str(i),
                    "logSource": "test",
                    "hostname": "test_hostname"
                })
            )

        assert len(component.train_data) == 2

    def test_training_keep_training(self) -> None:
        component = MockComponentWithTraining(name="Dummy6")
        component.fitlogic.train_state = TrainState.KEEP_TRAINING

        for i in range(10):
            component.process(
                schemas.LogSchema({
                    "__version__": "1.0.0",
                    "logID": str(i),
                    "logSource": "test",
                    "hostname": "test_hostname"
                })
            )

        assert len(component.train_data) == 10

    def _make_log(self, i: int) -> schemas.LogSchema:
        return schemas.LogSchema({
            "__version__": "1.0.0",
            "logID": str(i),
            "logSource": "test",
            "hostname": "test_hostname"
        })

    def test_configuration(self) -> None:
        component = MockComponentWithConfigure(name="DummyCfg1")

        results = [component.process(self._make_log(i)) for i in range(10)]

        assert component.fitlogic.data_used_configure == 3
        assert len(component.configure_data) == 3
        assert all(r is None for r in results[:3])
        assert component.set_configuration_called == 1

    def test_configuration_returns_none_during_configure(self) -> None:
        component = MockComponentWithConfigure(name="DummyCfg2")

        results = [component.process(self._make_log(i)) for i in range(3)]

        assert all(r is None for r in results)

    def test_configuration_force_stop(self) -> None:
        component = MockComponentWithConfigure(name="DummyCfg3")
        component.fitlogic.configure_state = ConfigState.STOP_CONFIGURE

        for i in range(10):
            component.process(self._make_log(i))

        assert len(component.configure_data) == 0
        assert component.set_configuration_called == 0

    def test_configuration_keep_configure(self) -> None:
        component = MockComponentWithConfigure(name="DummyCfg4")
        component.fitlogic.configure_state = ConfigState.KEEP_CONFIGURE

        for i in range(10):
            component.process(self._make_log(i))

        assert len(component.configure_data) == 10
        assert component.set_configuration_called == 0

    def test_configuration_before_training(self) -> None:
        config = CoreConfig(data_use_configure=2, data_use_training=3)
        component = MockComponentWithConfigureAndTraining(name="DummyCfg5", config=config)

        for i in range(10):
            component.process(self._make_log(i))

        assert len(component.configure_data) == 2
        assert len(component.train_data) == 3
        assert component.set_configuration_called == 1

    def test_set_configuration_called_once(self) -> None:
        component = MockComponentWithConfigure(name="DummyCfg6")

        for i in range(component.config.data_use_configure + 5):  # type: ignore[operator]
            component.process(self._make_log(i))

        assert component.set_configuration_called == 1
