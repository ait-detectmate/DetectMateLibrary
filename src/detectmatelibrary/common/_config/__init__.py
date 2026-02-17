from detectmatelibrary.common._config._compile import ConfigMethods, generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig

__all__ = ["ConfigMethods", "generate_detector_config", "EventsConfig", "BasicConfig"]

from pydantic import BaseModel, ConfigDict

from typing_extensions import Self
from typing import Any, Dict
from copy import deepcopy


class BasicConfig(BaseModel):
    """Base configuration class with helper methods."""

    model_config = ConfigDict(extra="forbid")

    method_type: str = "default_method_type"
    comp_type: str = "default_type"

    auto_config: bool = False

    def get_config(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self.model_dump()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update the configuration with new values."""
        for key, value in new_config.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], method_id: str) -> Self:
        aux = cls()
        config_ = ConfigMethods.get_method(
            deepcopy(data), comp_type=aux.comp_type, method_id=method_id
        )
        ConfigMethods.check_type(config_, method_type=aux.method_type)

        return cls(**ConfigMethods.process(config_))

    def to_dict(self, method_id: str) -> Dict[str, Any]:
        """Convert the config back to YAML-compatible dictionary format.

        This is the inverse of from_dict() and ensures yaml -> pydantic -> yaml preservation.

        Args:
            method_id: The method identifier to use in the output structure

        Returns:
            Dictionary with structure: {comp_type: {method_id: config_data}}
        """
        # Build the config in the format expected by from_dict
        result: Dict[str, Any] = {
            "method_type": self.method_type,
            "auto_config": self.auto_config,
        }

        # Collect all non-meta fields for params
        params = {}
        events_data = None

        for field_name, field_value in self:
            # Skip meta fields
            if field_name in ("comp_type", "method_type", "auto_config"):
                continue

            # Handle EventsConfig specially
            if field_name == "events":
                if field_value is not None:
                    if isinstance(field_value, EventsConfig):
                        events_data = field_value.to_dict()
                    else:
                        events_data = field_value
            else:
                # All other fields go into params
                params[field_name] = field_value

        # Add params if there are any
        if params:
            result["params"] = params

        # Add events if they exist
        if events_data is not None:
            result["events"] = events_data

        # Wrap in the comp_type and method_id structure
        return {
            self.comp_type: {
                method_id: result
            }
        }
