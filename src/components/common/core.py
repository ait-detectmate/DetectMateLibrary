
from typing import Any, Dict
from pydantic import BaseModel

from src.components.utils.DataBuffer import DataBuffer, ArgsBuffer
import src.schemas as schemas


class ConfigCore(BaseModel):
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
    def from_dict(cls, data: dict) -> "ConfigCore":
        """Create a ConfigCore instance from a dictionary."""
        return cls(**data)


class CoreComponent:
    """Base class for all components in the system."""
    def __init__(
        self,
        name: str,
        type_: str = "Base",
        config: ConfigCore = ConfigCore(),
        args_buffer: ArgsBuffer = ArgsBuffer("no_buf"),
        input_schema: schemas.SchemaID = schemas.BASE_SCHEMA,
        output_schema: schemas.SchemaID = schemas.BASE_SCHEMA
    ) -> None:

        self.name = name
        self.type_ = type_
        self.config = config
        self.input_schema, self.output_schema = input_schema, output_schema

        self.data_buffer = DataBuffer(args_buffer)

    def __repr__(self) -> str:
        return f"<{self.type_}> {self.name}: {self.config}"

    def process(self, data: schemas.SchemaT | bytes) -> schemas.SchemaT | bytes:
        is_byte = False
        if isinstance(data, bytes):
            schema_id, data = schemas.deserialize(data)
            is_byte = True
            schemas.check_is_same_schema(schema_id, self.input_schema)

        data = self.data_buffer.add(data)

        return data if not is_byte else schemas.serialize(self.output_schema, data)

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: dict) -> None:
        self.config.update_config(new_config)
