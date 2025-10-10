import pytest
import tempfile
import os
from pydantic import ValidationError

from src.config.app_config import AppConfig, load_config_from_yaml
from src.config.parsers import ParserConfig, ParserInstance
from src.config.detectors import DetectorConfig, DetectorInstance


class TestAppConfig:
    """Test the main AppConfig class."""

    def test_valid_config_creation(self):
        """Test creating a valid AppConfig with proper references."""
        parser_config = ParserConfig(
            type="ExampleParser",
            instances=[
                ParserInstance(id="parser1", log_format="<Content>"),
                ParserInstance(id="parser2", log_format="[<Time>] <Content>")
            ]
        )

        detector_config = DetectorConfig(
            type="ExampleDetector",
            parser="parser1",
            auto_config=False,
            instances=[
                DetectorInstance(id="detector1", event=1)
            ]
        )

        config = AppConfig(
            parsers=[parser_config],
            detectors=[detector_config]
        )

        assert len(config.parsers) == 1
        assert len(config.detectors) == 1
        assert config.detectors[0].parser == "parser1"

    def test_invalid_parser_reference(self):
        """Test that referencing non-existent parser raises ValidationError."""
        parser_config = ParserConfig(
            type="ExampleParser",
            instances=[ParserInstance(id="parser1", log_format="<Content>")]
        )

        detector_config = DetectorConfig(
            type="ExampleDetector",
            parser="non_existent_parser1",  # Invalid reference
            auto_config=False,
            instances=[DetectorInstance(id="detector1", event=1)]
        )

        with pytest.raises(ValidationError, match="references parser 'non_existent_parser1'"):
            AppConfig(
                parsers=[parser_config],
                detectors=[detector_config]
            )

    def test_detector_without_parser_reference(self):
        """Test that detector without parser reference is valid."""
        parser_config = ParserConfig(
            type="ExampleParser",
            instances=[ParserInstance(id="parser1")]
        )

        detector_config = DetectorConfig(
            type="AutoDetector",
            auto_config=True  # No parser reference needed for auto config
        )

        config = AppConfig(
            parsers=[parser_config],
            detectors=[detector_config]
        )

        assert config.detectors[0].parser is None

    def test_empty_config(self):
        """Test creating empty config."""
        config = AppConfig(parsers=[], detectors=[])
        assert len(config.parsers) == 0
        assert len(config.detectors) == 0


class TestLoadConfigFromYaml:
    """Test the load_config_from_yaml function."""

    def test_load_valid_yaml_config(self):
        """Test loading a valid YAML configuration."""
        yaml_content = """
parsers:
  - type: ExampleParser
    instances:
      - id: parser1
        log_format: "[<Time>] <Content>"

detectors:
  - type: ExampleDetector
    parser: parser1
    auto_config: false
    instances:
      - id: detector1
        event: 1
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config_from_yaml(f.name)
                assert isinstance(config, AppConfig)
                assert len(config.parsers) == 1
                assert len(config.detectors) == 1
                assert config.parsers[0].type == "ExampleParser"
                assert config.detectors[0].parser == "parser1"
            finally:
                os.unlink(f.name)

    def test_load_yaml_with_invalid_parser_reference(self):
        """Test loading YAML with invalid parser reference raises error."""
        yaml_content = """
parsers:
  - type: ExampleParser
    instances:
      - id: parser1

detectors:
  - type: ExampleDetector
    parser: invalid_parser
    auto_config: false
    instances:
      - id: detector1
        event: 1
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with pytest.raises(ValidationError):
                    load_config_from_yaml(f.name)
            finally:
                os.unlink(f.name)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config_from_yaml("nonexistent_file.yaml")
