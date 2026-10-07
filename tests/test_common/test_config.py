from detectmatelibrary.common._config._compile import (
    ConfigMethods,
    MethodNotFoundError,
    MissingParamsWarning,
    TypeNotFoundError,
    MethodTypeNotMatch,
)
from detectmatelibrary.common._config._formats import EventsConfig, _EventConfig
from detectmatelibrary.common._config import BasicConfig
from detectmatelibrary.common._config import AutoConfigParams
from detectmatelibrary.base_detectors import VariableDetectorConfig
from detectmatelibrary.detectors.bigram_frequency_detector import BigramFrequencyDetectorConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetectorConfig
from detectmatelibrary.detectors.logbert_detector import LogBertDetectorConfig
from detectmatelibrary.detectors.new_event_detector import NewEventDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetectorConfig
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.detectors.random_detector import RandomDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetectorConfig
from detectmatelibrary.detectors.scvs_detector import SCVSDetectorConfig
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetectorConfig
from detectmatelibrary.parsers.autoparser import AutoParserConfig
from detectmatelibrary.parsers.drain import DrainConfig
from detectmatelibrary.parsers.json_parser import JsonParserConfig
from detectmatelibrary.parsers.logbatcher import LogBatcherParserConfig
from detectmatelibrary.parsers.template_matcher import MatcherParserConfig
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig
from pydantic import BaseModel, ValidationError, Field
from tests.test_data import TEST_CONFIG
import pytest
import warnings
import yaml


def load_test_config() -> dict:
    with open(TEST_CONFIG, "r") as file:
        return yaml.safe_load(file)


config_test = load_test_config()

# Every config with a generated doc page (see docs/examples/config/update.py).
DOCUMENTED_CONFIGS = [
    BigramFrequencyDetectorConfig(), CharsetDetectorConfig(), DeeplogDetectorConfig(),
    ECVCDetectorConfig(), EventSequenceDetectorConfig(), LogBertDetectorConfig(),
    NewEventDetectorConfig(), NewValueComboDetectorConfig(), NewValueDetectorConfig(),
    RandomDetectorConfig(), RuleDetectorConfig(), SCVSDetectorConfig(), ValueRangeDetectorConfig(),
    AutoParserConfig(), DrainConfig(), JsonParserConfig(), LogBatcherParserConfig(),
    MatcherParserConfig(), TemplateCppTreeMatcherConfig(),
]


class DummyConfigDoc(BasicConfig):
    hello: str | None = Field(default="Hello", description="a way to salute people")
    dont_show: str = Field(default="a", description="<$IGNORE$> dont show stuff")
    auto_config: bool = Field(
        default=True,
        description="Runs the configuration step before the training process.",
    )


class DummyInnerParams(BaseModel):
    flag: bool = Field(default=True, description="an inner flag")


class DummyAutoParams(AutoConfigParams):
    size: int = Field(default=3, description="how big")
    inner: DummyInnerParams = DummyInnerParams()


class DummyConfigWithAuto(BasicConfig):
    auto_config_params: DummyAutoParams = DummyAutoParams()


def _row(docs: list[dict], name: str, block: str | None = None) -> dict:
    matches = [r for r in docs if r["Name"] == name and (block is None or r["Block"] == block)]
    assert len(matches) == 1, f"expected one row for {name!r}, got {matches}"
    return matches[0]


class TestConfigDocs:
    def test_get_configs(self):
        docs = BasicConfig().get_docs()

        assert len(docs) == 3
        assert {
            "Name": "method_type",
            "Block": "top",
            "Type": "string",
            "Default value": "default_method_type",
            "Scope": "specific",
            "Default changed": False,
            "Shared default": None,
            "Description": "Indicates what type of method is.",
        } in docs
        assert _row(docs, "component_type")["Block"] == "top"
        assert _row(docs, "auto_config")["Default value"] is False

    def test_inherent_class_docs(self):
        docs = DummyConfigDoc().get_docs(shared_base=BasicConfig)

        assert len(docs) == 4
        hello = _row(docs, "hello")
        assert hello["Block"] == "params"
        assert hello["Type"] == "string, null"
        assert hello["Scope"] == "specific"
        assert not hello["Default changed"]

        auto_config = _row(docs, "auto_config")
        assert auto_config["Block"] == "top"
        assert auto_config["Scope"] == "shared"
        assert auto_config["Default value"] is True
        assert auto_config["Default changed"]
        assert auto_config["Shared default"] is False

        assert _row(docs, "method_type")["Scope"] == "shared"

    def test_ignored_fields_are_hidden(self):
        names = [r["Name"] for r in DummyConfigDoc().get_docs()]
        assert "dont_show" not in names

    def test_auto_config_params_flattened(self):
        docs = DummyConfigWithAuto().get_docs(shared_base=BasicConfig)

        size = _row(docs, "size", block="auto_config_params")
        assert size["Scope"] == "specific"
        assert size["Default value"] == 3
        flag = _row(docs, "inner.flag", block="auto_config_params")
        assert flag["Type"] == "boolean"
        assert flag["Description"] == "an inner flag"
        assert "auto_config_params" not in [r["Name"] for r in docs]

    def test_nested_scope_against_family_base(self):
        docs = NewValueComboDetectorConfig().get_docs(shared_base=VariableDetectorConfig)

        assert _row(docs, "max_combo_size", "auto_config_params")["Scope"] == "specific"
        assert _row(docs, "use_stable_vars", "auto_config_params")["Scope"] == "shared"
        static = _row(docs, "use_static_vars", "auto_config_params")
        assert static["Scope"] == "shared"
        assert static["Default value"] is False
        assert static["Default changed"]
        assert static["Shared default"] is True
        decision = _row(docs, "classification.decision", "auto_config_params")
        assert decision["Scope"] == "shared"
        assert not decision["Default changed"]

    def test_top_level_detector_fields(self):
        docs = NewValueComboDetectorConfig().get_docs(shared_base=VariableDetectorConfig)

        assert _row(docs, "global")["Block"] == "top"
        assert _row(docs, "events")["Block"] == "top"
        persist = _row(docs, "persist")
        assert persist["Block"] == "top"
        assert persist["Type"] == "object, null"
        assert _row(docs, "start_id")["Block"] == "params"
        # method_type differs on every detector -- not flagged as a changed default
        assert not _row(docs, "method_type")["Default changed"]

    @pytest.mark.parametrize("config", DOCUMENTED_CONFIGS, ids=lambda c: type(c).__name__)
    def test_every_documented_field_has_a_description(self, config):
        missing = [r["Name"] for r in config.get_docs() if r["Description"] == "No description provided."]
        assert missing == []


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


class MockupParserConfig(BasicConfig):
    method_type: str = "ExampleParser"
    component_type: str = "parsers"

    auto_config: bool = False
    log_format: str = "<PLACEHOLDER>"
    depth: int = -1


class MockuptDetectorConfig(BasicConfig):
    method_type: str = "ExampleDetector"
    component_type: str = "detectors"
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
