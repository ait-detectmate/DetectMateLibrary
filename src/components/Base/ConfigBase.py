from typing import Any, Dict
from pydantic import BaseModel


class ConfigBase(BaseModel):
    """Base configuration class with helper methods."""

    # Forbid extra fields not defined in subclasses (via pydantic)
    class Config:
        extra = "forbid"

    def get_config(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self.model_dump()

    def update_config(self, new_config: dict) -> None:
        """Update the configuration with new values."""
        validated = self.model_validate(new_config, strict=True)
        for key, value in validated.model_dump().items():
            setattr(self, key, value)
