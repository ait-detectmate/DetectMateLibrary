

from detectmatelibrary.utils.config import (
    ConfigMethods,
    MethodNotFoundError,
    TypeNotFoundError,
    MethodTypeNotMatch,
    AutoConfigError,
    AutoConfigWarning
)

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
        with pytest.raises(AutoConfigError):
            ConfigMethods.process(ConfigMethods.get_method(
                config_test, method_id="detector_wrong", comp_type="detectors"
            ))

    def test_process_auto_config_warning(self):
        with pytest.warns(AutoConfigWarning):
            ConfigMethods.process(ConfigMethods.get_method(
                config_test, method_id="detector_weird", comp_type="detectors"
            ))
