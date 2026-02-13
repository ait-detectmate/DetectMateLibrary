"""Test that YAML -> Pydantic -> YAML is preserved (round-trip test)."""

from detectmatelibrary.common._config import BasicConfig
from detectmatelibrary.common._config._formats import EventsConfig

import yaml


class MockupParserConfig(BasicConfig):
    method_type: str = "ExampleParser"
    comp_type: str = "parsers"
    auto_config: bool = False
    log_format: str = "<PLACEHOLDER>"
    depth: int = -1


class MockupDetectorConfig(BasicConfig):
    method_type: str = "ExampleDetector"
    comp_type: str = "detectors"
    auto_config: bool = False
    parser: str = "<PLACEHOLDER>"
    events: EventsConfig | None = None


def load_test_config() -> dict:
    with open("tests/test_folder/test_config.yaml", 'r') as file:
        return yaml.safe_load(file)


class TestConfigRoundtrip:
    """Test that yaml -> pydantic class -> yaml is preserved."""

    def test_parser_roundtrip_simple(self):
        """Test parser config without events."""
        config_yaml = load_test_config()
        method_id = "example_parser"

        # Load from YAML
        config = MockupParserConfig.from_dict(config_yaml, method_id)

        # Convert back to dict
        result_dict = config.to_dict(method_id)

        # Extract the original and result configs
        original = config_yaml["parsers"][method_id]
        result = result_dict["parsers"][method_id]

        # Compare all fields
        assert result["method_type"] == original["method_type"]
        assert result["auto_config"] == original["auto_config"]
        assert result["params"]["log_format"] == original["params"]["log_format"]
        assert result["params"]["depth"] == original["params"]["depth"]

    def test_detector_roundtrip_with_events(self):
        """Test detector config with events structure."""
        config_yaml = load_test_config()
        method_id = "detector_variables"

        # Load from YAML
        config = MockupDetectorConfig.from_dict(config_yaml, method_id)

        # Convert back to dict
        result_dict = config.to_dict(method_id)

        # Extract the original and result configs
        original = config_yaml["detectors"][method_id]
        result = result_dict["detectors"][method_id]

        # Compare basic fields
        assert result["method_type"] == original["method_type"]
        assert result["auto_config"] == original["auto_config"]
        # parser is in params after to_dict (normalized format)
        assert result["params"]["parser"] == original["parser"]

        # Compare events structure
        assert "events" in result
        assert 1 in result["events"]  # event_id = 1
        assert "example_detector_1" in result["events"][1]  # instance_id

        instance = result["events"][1]["example_detector_1"]
        original_instance = original["events"][1]["example_detector_1"]

        # Check variables
        assert len(instance["variables"]) == len(original_instance["variables"])

        zipped = zip(instance["variables"], original_instance["variables"])
        for i, (result_var, orig_var) in enumerate(zipped):
            assert result_var["pos"] == orig_var["pos"]
            assert result_var["name"] == orig_var["name"]
            if "params" in orig_var:
                assert result_var["params"] == orig_var["params"]

    def test_detector_roundtrip_auto_config(self):
        """Test detector with auto_config = True."""
        config_yaml = load_test_config()
        method_id = "detector_auto"

        # Load from YAML
        config = MockupDetectorConfig.from_dict(config_yaml, method_id)

        # Convert back to dict
        result_dict = config.to_dict(method_id)

        # Extract configs
        original = config_yaml["detectors"][method_id]
        result = result_dict["detectors"][method_id]

        # Compare
        assert result["method_type"] == original["method_type"]
        assert result["auto_config"] == original["auto_config"]
        assert result["auto_config"] is True
        assert result["params"]["parser"] == original["parser"]

    def test_full_yaml_roundtrip(self):
        """Test that the entire structure can be serialized and matches."""
        config_yaml = load_test_config()

        # Test parser
        parser_config = MockupParserConfig.from_dict(config_yaml, "example_parser")
        parser_dict = parser_config.to_dict("example_parser")

        # Verify parser structure exists
        assert "parsers" in parser_dict
        assert "example_parser" in parser_dict["parsers"]
        assert "method_type" in parser_dict["parsers"]["example_parser"]

        # Test detector with events
        detector_config = MockupDetectorConfig.from_dict(config_yaml, "detector_variables")
        detector_dict = detector_config.to_dict("detector_variables")

        # Verify detector structure exists
        assert "detectors" in detector_dict
        assert "detector_variables" in detector_dict["detectors"]
        assert "events" in detector_dict["detectors"]["detector_variables"]

    def test_empty_params_preserved(self):
        """Test that empty params dict is preserved."""
        config_yaml = load_test_config()
        method_id = "detector_variables"

        config = MockupDetectorConfig.from_dict(config_yaml, method_id)
        result_dict = config.to_dict(method_id)

        # Instance level params
        instance = result_dict["detectors"][method_id]["events"][1]["example_detector_1"]
        assert "params" in instance
        assert instance["params"] == {}

    def test_header_variables_roundtrip(self):
        """Test that header_variables are preserved."""
        config_yaml = load_test_config()
        method_id = "detector_variables"  # This one has header_variables

        config = MockupDetectorConfig.from_dict(config_yaml, method_id)
        result_dict = config.to_dict(method_id)

        instance = result_dict["detectors"][method_id]["events"][1]["example_detector_1"]
        original_instance = config_yaml["detectors"][method_id]["events"][1]["example_detector_1"]

        # Check header variables exist
        assert "header_variables" in instance
        assert len(instance["header_variables"]) == len(original_instance["header_variables"])

        zipped = zip(
            instance["header_variables"], original_instance["header_variables"]
        )
        for result_hvar, orig_hvar in zipped:
            assert result_hvar["pos"] == orig_hvar["pos"]
            if "params" in orig_hvar:
                assert result_hvar["params"] == orig_hvar["params"]

    def test_no_events_field_when_none(self):
        """Test that events field is not included when it doesn't exist."""
        config_yaml = load_test_config()
        method_id = "example_parser"

        config = MockupParserConfig.from_dict(config_yaml, method_id)
        result_dict = config.to_dict(method_id)

        # Parser should not have events field
        assert "events" not in result_dict["parsers"][method_id]

    def test_true_roundtrip_preservation(self):
        """Test that yaml -> pydantic -> yaml -> pydantic produces identical
        objects."""
        config_yaml = load_test_config()
        method_id = "detector_variables"

        # First load
        config1 = MockupDetectorConfig.from_dict(config_yaml, method_id)

        # Convert back to dict
        dict1 = config1.to_dict(method_id)

        # Second load from the converted dict
        config2 = MockupDetectorConfig.from_dict(dict1, method_id)

        # Convert back again
        dict2 = config2.to_dict(method_id)

        # The two configs should be identical
        assert config1.method_type == config2.method_type
        assert config1.comp_type == config2.comp_type
        assert config1.auto_config == config2.auto_config
        assert config1.parser == config2.parser

        # Events should match
        assert config1.events is not None
        assert config2.events is not None

        # Check event structure matches
        for event_id in config1.events.events.keys():
            assert event_id in config2.events.events
            for instance_id in config1.events.events[event_id].instances.keys():
                assert instance_id in config2.events.events[event_id].instances

                inst1 = config1.events.events[event_id].instances[instance_id]
                inst2 = config2.events.events[event_id].instances[instance_id]

                # Check variables match
                assert len(inst1.variables) == len(inst2.variables)
                for pos in inst1.variables.keys():
                    assert pos in inst2.variables
                    assert inst1.variables[pos].name == inst2.variables[pos].name
                    assert inst1.variables[pos].params == inst2.variables[pos].params

                # Check header_variables match
                assert len(inst1.header_variables) == len(inst2.header_variables)
                for pos in inst1.header_variables.keys():
                    assert pos in inst2.header_variables
                    assert inst1.header_variables[pos].params == inst2.header_variables[pos].params

        # The two dicts should be identical
        assert dict1 == dict2

    def test_parser_true_roundtrip(self):
        """Test parser yaml -> pydantic -> yaml -> pydantic roundtrip."""
        config_yaml = load_test_config()
        method_id = "example_parser"

        # First load
        config1 = MockupParserConfig.from_dict(config_yaml, method_id)

        # Convert back to dict and reload
        dict1 = config1.to_dict(method_id)
        config2 = MockupParserConfig.from_dict(dict1, method_id)
        dict2 = config2.to_dict(method_id)

        # Compare
        assert config1.method_type == config2.method_type
        assert config1.log_format == config2.log_format
        assert config1.depth == config2.depth
        assert config1.auto_config == config2.auto_config

        # Dicts should be identical
        assert dict1 == dict2
