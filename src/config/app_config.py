"""Main application configuration class."""

from __future__ import annotations
from typing import List
from pydantic import BaseModel, model_validator

from .parsers import ParserConfig
from .detectors import DetectorConfig


class AppConfig(BaseModel):
    parsers: List[ParserConfig]
    detectors: List[DetectorConfig]

    @model_validator(mode="after")
    def _validate_cross_refs(self):
        # Build a set of all valid parser instance IDs
        parser_instance_ids = {
            inst.id
            for parser in self.parsers
            for inst in parser.instances
        }

        # Check that any detector.parser (if provided) references an existing parser instance
        for det in self.detectors:
            if det.parser is not None and det.parser not in parser_instance_ids:
                raise ValueError(
                    f"Detector '{det.type}' references parser '{det.parser}', "
                    f"but no ParserInstance with that id exists."
                )
        return self


def load_config_from_yaml(file_path: str, configClass=AppConfig) -> AppConfig:
    """Parse your YAML string into the AppConfig model."""
    import yaml  # PyYAML
    with open(file_path, 'r') as file:
        try:
            yaml_data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(f"Error while loading YAML file: {e}")
    return configClass.model_validate(yaml_data)
