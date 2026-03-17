

from detectmatelibrary.common._config._compile import (
    ConfigMethods,
    MethodNotFoundError,
    MissingParamsWarning,
    TypeNotFoundError,
    MethodTypeNotMatch,
    AutoConfigWarning,
)
from detectmatelibrary.common._config._formats import (
    EventsConfig, _EventConfig
)
from detectmatelibrary.common._config import BasicConfig

from pydantic import ValidationError
import pytest
import yaml


def load_test_config() -> dict:
    with open("tests/test_folder/test_config.yaml", 'r') as file:
        return yaml.safe_load(file)


config_test = load_test_config()


class TestConfigMethods:
    def test_get_method(self):
        config = ConfigMethods.get_method(
            config_test, method_id="example_parser", comp_type="parsers"
        )
        assert config["method_type"] == "ExampleParser"
        assert not config["auto_config"]
        assert config["params"] == {
            "log_format": "[<Time>] [<Level>] <Content>", "depth": 4
        }

    def test_method_not_found(self):
        with pytest.raises(MethodNotFoundError):
            ConfigMethods.get_method(
                config_test, method_id="non_existent", comp_type="parsers"
            )

    def test_type_not_found(self):
        with pytest.raises(TypeNotFoundError):
            ConfigMethods.get_method(
                config_test, method_id="example_parser", comp_type="non_existent_type"
            )

    def test_check_type(self):
        config = ConfigMethods.get_method(
            config_test, method_id="example_parser", comp_type="parsers"
        )
        ConfigMethods.check_type(config, method_type="ExampleParser")

        with pytest.raises(MethodTypeNotMatch):
            ConfigMethods.check_type(config, method_type="IncorrectOne")

    def test_process_simple(self):
        config = ConfigMethods.process(ConfigMethods.get_method(
            config_test, method_id="example_parser", comp_type="parsers"
        ))

        assert config["method_type"] == "ExampleParser"
        assert not config["auto_config"]
        assert config["log_format"] == "[<Time>] [<Level>] <Content>"
        assert config["depth"] == 4
        assert "params" not in config

    def test_process_auto_config(self):
        config = ConfigMethods.process(ConfigMethods.get_method(
            config_test, method_id="detector_auto", comp_type="detectors"
        ))

        assert config["method_type"] == "ExampleDetector"
        assert config["auto_config"]
        assert config["parser"] == "example_parser_1"
        assert "params" not in config

    def test_process_auto_config_false(self):
        with pytest.warns(MissingParamsWarning):
            ConfigMethods.process(ConfigMethods.get_method(
                config_test, method_id="detector_wrong", comp_type="detectors"
            ))

    def test_process_auto_config_warning(self):
        with pytest.warns(AutoConfigWarning):
            ConfigMethods.process(ConfigMethods.get_method(
                config_test, method_id="detector_weird", comp_type="detectors"
            ))


class TestParamsFormat:
    def test_correct_format(self):
        config_test = load_test_config()
        config = ConfigMethods.process(ConfigMethods.get_method(
            config_test, method_id="detector_variables", comp_type="detectors"
        ))

        assert config["method_type"] == "ExampleDetector"
        assert config["parser"] == "example_parser_1"
        assert not config["auto_config"]
        assert isinstance(config["events"], EventsConfig)

        # Get the event config for event_id 1
        event_config = config["events"][1]
        assert isinstance(event_config, _EventConfig)

        # Check variables via pass-through properties
        assert event_config.variables[0].pos == 0
        assert event_config.variables[0].name == "child_process"
        assert event_config.variables[0].params == {"threshold": 0.5}

        assert event_config.header_variables["Level"].pos == "Level"
        assert event_config.header_variables["Level"].params == {"threshold": 0.2}

    def test_correct_format2(self):
        config = ConfigMethods.process(ConfigMethods.get_method(
            config_test, method_id="detector_variables2", comp_type="detectors"
        ))

        assert config["method_type"] == "ExampleDetector"
        assert config["parser"] == "example_parser_1"
        assert not config["auto_config"]
        assert isinstance(config["events"], EventsConfig)

        # Get the event config for event_id 1
        event_config = config["events"][1]
        assert isinstance(event_config, _EventConfig)

        assert len(event_config.variables) == 0

        assert event_config.header_variables["Level"].pos == "Level"
        assert event_config.header_variables["Level"].params == {"threshold": 0.2}

    def test_return_none_if_not_found(self):
        config_test = load_test_config()
        config = ConfigMethods.process(ConfigMethods.get_method(
            config_test, method_id="detector_variables", comp_type="detectors"
        ))

        assert isinstance(config["events"][1], _EventConfig)
        assert config["events"]["NotExisting"] is None

    def test_get_dict(self):
        config_test = load_test_config()
        config = ConfigMethods.process(ConfigMethods.get_method(
            config_test, method_id="detector_variables", comp_type="detectors"
        ))
        variables = config["events"][1].get_all()

        assert len(variables) == 4

    def test_incorrect_format(self):
        with pytest.raises(ValidationError):
            ConfigMethods.process(ConfigMethods.get_method(
                config_test, method_id="detector_incorrect_format1", comp_type="detectors"
            ))


class MockupParserConfig(BasicConfig):
    method_type: str = "ExampleParser"
    comp_type: str = "parsers"

    auto_config: bool = False
    log_format: str = "<PLACEHOLDER>"
    depth: int = -1


class MockuptDetectorConfig(BasicConfig):
    method_type: str = "ExampleDetector"
    comp_type: str = "detectors"
    parser: str = "<PLACEHOLDER>"


class TestBasicConfig:
    def test_parser_from_dict(self):
        config_test = load_test_config()
        config = MockupParserConfig.from_dict(config_test, "example_parser")

        assert not config.auto_config
        assert config.log_format == "[<Time>] [<Level>] <Content>"
        assert config.depth == 4

    def test_detectir_from_dict(self):
        config_test = load_test_config()
        config = MockuptDetectorConfig.from_dict(config_test, "detector_auto")

        assert config.auto_config
        assert config.parser == "example_parser_1"
