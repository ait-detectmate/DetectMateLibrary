"""Tests for detectmatelibrary.common._config."""
from detectmatelibrary.common._config import BasicConfig
from detectmatelibrary.common._config import AutoConfigParams
from detectmatelibrary.base_detectors import VariableDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetectorConfig
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from pydantic import BaseModel, Field
from tests.support.paths import TEST_CONFIG
import pytest
import yaml
from detectmatelibrary.common.core import CoreConfig
import pydantic
import warnings
from detectmatelibrary.common._config._compile import MissingParamsWarning
from detectmatelibrary.base_detectors import PersistConfig


def load_test_config() -> dict:
    with open(TEST_CONFIG, "r") as file:
        return yaml.safe_load(file)


config_test = load_test_config()


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


class MockConfig(CoreConfig):
    thresholds: float = 0.7
    max_iter: int = 50


default_args = {
    "method_type": "default_method_type",
    "component_type": "default_type",
    "auto_config": False,
    "auto_config_params": {},
    "start_id": 10,
    "data_use_training": None,
    "data_use_configure": None,
    "use_config_data_as_training": True,
    "train_buffer_max_records": 100_000,
    "train_buffer_dir": None,
    'connector_name': None,
    'connector_url': None
}


class TestConfigCore:
    def test_initialize(self) -> None:
        config = MockConfig(thresholds=0.5, max_iter=100)
        expected = {"thresholds": 0.5, "max_iter": 100, 'connector_name': None, 'connector_url': None}
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
        expected = {"thresholds": 0.8, "max_iter": 30, 'connector_name': None, 'connector_url': None}
        expected.update(default_args)
        expected["data_use_training"] = 10

        assert isinstance(config, BasicConfig)
        assert config.get_config() == expected

    def test_incorect_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockConfig(thresholds="high", max_iter="many")

    def test_update_config(self) -> None:
        config = MockConfig()

        expected = {
            "thresholds": 0.7,
            "max_iter": 50,
            "data_use_training": None,
            'connector_name': None,
            'connector_url': None
        }
        expected.update(default_args)
        assert config.get_config() == expected

        expected = {
            "thresholds": 0.9,
            "max_iter": 50,
            "data_use_training": None,
            'connector_name': None,
            'connector_url': None
        }
        expected.update(default_args)
        config.update_config({"thresholds": 0.9})
        assert config.get_config() == expected

        expected = {
            "max_iter": 200,
            "thresholds": 0.9,
            "data_use_training": None,
            'connector_name': None,
            'connector_url': None
        }
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


class TestPersistConfigSerialization:
    def test_to_dict_places_persist_at_top_level(self):
        config = NewValueDetectorConfig(
            auto_config=True,
            persist=PersistConfig(path="./my-state", interval_seconds=60),
        )
        result = config.to_dict("MyDet")
        inner = result["detectors"]["MyDet"]
        assert "persist" in inner
        assert inner["persist"]["path"] == "./my-state"
        assert inner["persist"]["interval_seconds"] == 60
        assert "persist" not in inner.get("params", {})

    def test_to_dict_omits_persist_when_none(self):
        config = NewValueDetectorConfig(auto_config=True)
        result = config.to_dict("MyDet")
        inner = result["detectors"]["MyDet"]
        assert "persist" not in inner

    def test_from_dict_loads_persist_block(self):
        config_dict = {
            "detectors": {
                "MyDet": {
                    "method_type": "new_value_detector",
                    "auto_config": True,
                    "persist": {"path": "./my-state", "interval_seconds": 60},
                }
            }
        }
        config = NewValueDetectorConfig.from_dict(config_dict, "MyDet")
        assert config.persist is not None
        assert config.persist.path == "./my-state"
        assert config.persist.interval_seconds == 60

    def test_roundtrip_yaml_to_pydantic_to_yaml(self):
        config_dict = {
            "detectors": {
                "MyDet": {
                    "method_type": "new_value_detector",
                    "auto_config": True,
                    "persist": {"path": "./my-state"},
                }
            }
        }
        config = NewValueDetectorConfig.from_dict(config_dict, "MyDet")
        result = config.to_dict("MyDet")
        assert result["detectors"]["MyDet"]["persist"]["path"] == "./my-state"

    def test_no_missing_params_warning_with_persist_only(self):
        config_dict = {
            "detectors": {
                "MyDet": {
                    "method_type": "new_value_detector",
                    "auto_config": False,
                    "persist": {"path": "./state"},
                }
            }
        }
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NewValueDetectorConfig.from_dict(config_dict, "MyDet")
        missing_params_warnings = [x for x in w if issubclass(x.category, MissingParamsWarning)]
        assert len(missing_params_warnings) == 0
