from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict


class BasicConfig(BaseModel):
    """Base configuration class with helper methods."""

    # Forbid extra fields not defined in subclasses (via pydantic)
    class Config:
        extra = "forbid"

    def get_config(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self.model_dump()

    def update_config(self, new_config: dict) -> None:
        """Update the configuration with new values."""
        for key, value in new_config.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: dict) -> "BasicConfig":
        """Create a ConfigCore instance from a dictionary."""
        return cls(**data)


test_time = False


def time_test_mode(new_value: bool = True) -> None:
    global test_time
    test_time = new_value


def get_timestamp() -> int:
    if test_time:
        return 0

    return int(datetime.now().timestamp())
