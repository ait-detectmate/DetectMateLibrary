from pydantic import BaseModel

import yaml


def load_config_from_yaml(file_path: str, configClass: BaseModel) -> BaseModel:
    """Parse your YAML string into the AppConfig model."""
    with open(file_path, 'r') as file:
        try:
            yaml_data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(f"Error while loading YAML file: {e}")
    return configClass.model_validate(yaml_data)
