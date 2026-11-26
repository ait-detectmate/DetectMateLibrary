"""Tests for detectmatelibrary.common._config._compile."""
from detectmatelibrary.common._config._compile import (
    ConfigMethods,
    MethodNotFoundError,
    MissingParamsWarning,
    TypeNotFoundError,
    MethodTypeNotMatch,
    get_configured_variables,
    get_global_variables,
)
from detectmatelibrary.common._config._formats import EventsConfig, _EventConfig
from detectmatelibrary.schemas import ParserSchema
from pydantic import ValidationError
from tests.support.paths import TEST_CONFIG
import pytest
import warnings
import yaml
from detectmatelibrary.common._config import generate_detector_config


def load_test_config() -> dict:
    with open(TEST_CONFIG, "r") as file:
        return yaml.safe_load(file)


config_test = load_test_config()


class TestConfigMethods:
    def test_get_method(self):
        config = ConfigMethods.get_method(
            config_test, method_id="example_parser", component_type="parsers"
        )
        assert config["method_type"] == "ExampleParser"
        assert not config["auto_config"]
        assert config["params"] == {
            "log_format": "[<Time>] [<Level>] <Content>",
            "depth": 4,
        }

    def test_method_not_found(self):
        with pytest.raises(MethodNotFoundError):
            ConfigMethods.get_method(
                config_test, method_id="non_existent", component_type="parsers"
            )

    def test_type_not_found(self):
        with pytest.raises(TypeNotFoundError):
            ConfigMethods.get_method(
                config_test,
                method_id="example_parser",
                component_type="non_existent_type",
            )

    def test_check_type(self):
        config = ConfigMethods.get_method(
            config_test, method_id="example_parser", component_type="parsers"
        )
        ConfigMethods.check_type(config, method_type="ExampleParser")

        with pytest.raises(MethodTypeNotMatch):
            ConfigMethods.check_type(config, method_type="IncorrectOne")

    def test_process_simple(self):
        config = ConfigMethods.process(
            ConfigMethods.get_method(
                config_test, method_id="example_parser", component_type="parsers"
            )
        )

        assert config["method_type"] == "ExampleParser"
        assert not config["auto_config"]
        assert config["log_format"] == "[<Time>] [<Level>] <Content>"
        assert config["depth"] == 4
        assert "params" not in config

    def test_process_auto_config(self):
        config = ConfigMethods.process(
            ConfigMethods.get_method(
                config_test, method_id="detector_auto", component_type="detectors"
            )
        )

        assert config["method_type"] == "ExampleDetector"
        assert config["auto_config"]
        assert config["parser"] == "example_parser_1"
        assert "params" not in config

    def test_process_auto_config_false(self):
        with pytest.warns(MissingParamsWarning):
            ConfigMethods.process(
                ConfigMethods.get_method(
                    config_test, method_id="detector_wrong", component_type="detectors"
                )
            )

    def test_process_keeps_params_under_auto_config(self):
        """params are operational and survive the configure phase, so
        auto_config: True alongside params is no longer suspicious."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            config = ConfigMethods.process(
                ConfigMethods.get_method(
                    config_test, method_id="detector_weird", component_type="detectors"
                )
            )
        assert config["auto_config"] is True
        assert config["hello"] == "a"


class TestParamsFormat:
    def test_correct_format(self):
        config_test = load_test_config()

        config = ConfigMethods.process(
            ConfigMethods.get_method(
                config_test, method_id="detector_variables", component_type="detectors"
            )
        )

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
        config = ConfigMethods.process(
            ConfigMethods.get_method(
                config_test, method_id="detector_variables2", component_type="detectors"
            )
        )

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

        config = ConfigMethods.process(
            ConfigMethods.get_method(
                config_test, method_id="detector_variables", component_type="detectors"
            )
        )

        assert isinstance(config["events"][1], _EventConfig)
        assert config["events"]["NotExisting"] is None

    def test_get_dict(self):
        config_test = load_test_config()

        config = ConfigMethods.process(
            ConfigMethods.get_method(
                config_test, method_id="detector_variables", component_type="detectors"
            )
        )
        variables = config["events"][1].get_all()

        assert len(variables) == 4

    def test_incorrect_format(self):
        with pytest.raises(ValidationError):
            ConfigMethods.process(
                ConfigMethods.get_method(
                    config_test,
                    method_id="detector_incorrect_format1",
                    component_type="detectors",
                )
            )


class TestGenerateDetectorConfig:
    def test_generate_detector_config_basic(self):
        """Test basic config generation with single event."""
        variable_selection = {
            1: ["var_0", "var_1"]
        }

        config_dict = generate_detector_config(
            variable_selection=variable_selection,
            detector_name="TestDetector",
            method_type="new_value_combo_detector",
            max_combo_size=2
        )

        assert "detectors" in config_dict
        assert "TestDetector" in config_dict["detectors"]
        detector_config = config_dict["detectors"]["TestDetector"]
        assert detector_config["method_type"] == "new_value_combo_detector"
        assert detector_config["params"]["max_combo_size"] == 2
        assert len(detector_config["events"]) == 1

    def test_generate_detector_config_multiple_events(self):
        """Test config generation with multiple events."""
        variable_selection = {
            1: ["var_0", "var_1"],
            2: ["var_0", "var_2", "var_3"],
            3: ["level"]
        }

        config_dict = generate_detector_config(
            variable_selection=variable_selection,
            detector_name="MultiEventDetector",
            method_type="new_value_combo_detector"
        )

        assert len(config_dict["detectors"]["MultiEventDetector"]["events"]) == 3


class TestVariableExtraction:
    """get_configured_variables / get_global_variables take what the config
    names from a parsed log, and skip what the log lacks."""

    log = ParserSchema({"eventID": 1, "variables": ["alice", "10.0.0.1"],
                        "headerVariables": {"Level": "INFO"}})

    def test_configured_variables_by_position_and_header_name(self):
        events = EventsConfig._init({1: {"inst": {
            "variables": [{"pos": 0, "name": "user"}, {"pos": 5, "name": "beyond"}],
            "header_variables": [{"pos": "Level"}, {"pos": "Missing"}]}}})
        assert get_configured_variables(self.log, events) == {"user": "alice", "Level": "INFO"}

    def test_an_unconfigured_event_gives_nothing(self):
        assert get_configured_variables(self.log, EventsConfig._init({2: {"inst": {}}})) == {}

    def test_a_plain_dict_entry_names_no_variables(self):
        assert get_configured_variables(self.log, {1: {}}) == {}

    def test_global_variables_skip_headers_the_log_lacks(self):
        instances = EventsConfig._init({"*": {"global": {
            "header_variables": [{"pos": "Level"}, {"pos": "Hostname"}]}}})["*"].instances
        assert get_global_variables(self.log, instances) == {"Level": "INFO"}
