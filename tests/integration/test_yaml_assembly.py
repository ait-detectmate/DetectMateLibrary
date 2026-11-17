"""Builds components from tests/test_data/test_config.yaml: each takes the
entry under its own instance name."""
import pytest
import yaml

from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector
from detectmatelibrary.detectors.new_value_detector import NewValueDetector
from detectmatelibrary.detectors.random_detector import RandomDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support.paths import TEST_CONFIG, TEST_TEMPLATES


@pytest.fixture
def config() -> dict:
    with open(TEST_CONFIG) as file:
        config = yaml.safe_load(file)
    # the YAML names its templates file relative to the repository root
    config["parsers"]["MatcherParser"]["params"]["path_templates"] = TEST_TEMPLATES
    return config


@pytest.mark.parametrize("component_cls, name", [
    (MatcherParser, "MatcherParser"),
    (RandomDetector, "RandomDetector"),
    (NewValueDetector, "NewValueDetector"),
    (NewValueDetector, "NewValueDetector_All"),
    (NewValueComboDetector, "NewValueComboDetector"),
    (NewValueComboDetector, "NewValueComboDetector_All"),
])
def test_component_takes_the_entry_of_its_name(component_cls, name, config):
    component = component_cls(name=name, config=config)
    entry = config[component.config.component_type][name]

    assert component.name == name
    assert component.config.method_type == entry["method_type"]
    assert component.config.auto_config == entry["auto_config"]
    for setting in ("parser", "path_templates"):
        expected = entry.get(setting, entry.get("params", {}).get(setting))
        if expected is not None:
            assert getattr(component.config, setting) == expected
