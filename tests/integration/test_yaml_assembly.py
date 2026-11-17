"""Builds every component from tests/test_data/test_config.yaml."""
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector
from detectmatelibrary.detectors.new_value_detector import NewValueDetector
from detectmatelibrary.detectors.random_detector import RandomDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support.paths import TEST_CONFIG, TEST_TEMPLATES
import yaml


class TestExamples:
    def test_config_example(self) -> None:
        with open(TEST_CONFIG, 'r') as file:
            config = yaml.safe_load(file)
        # The YAML names its templates file relative to the repository root.
        config["parsers"]["MatcherParser"]["params"]["path_templates"] = TEST_TEMPLATES

        # Nothing should crash

        # Parsers
        MatcherParser(config=config)

        # Detectors
        RandomDetector(config=config)

        NewValueDetector(config=config)
        NewValueDetector(config=config, name="NewValueDetector_All")

        NewValueComboDetector(config=config)
        NewValueComboDetector(config=config, name="NewValueComboDetector_All")
