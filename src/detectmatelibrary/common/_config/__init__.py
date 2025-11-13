from detectmatelibrary.common._config._compile import ConfigMethods

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
