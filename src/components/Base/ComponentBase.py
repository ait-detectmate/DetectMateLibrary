
from typing import Any, Literal, Optional, Dict
from pydantic import BaseModel
from abc import ABC

from src.schemas import ANY_SCHEMA, serialize, deserialize, check_is_same_schema, SchemaID
from src.components.utils.DataBuffer import DataBuffer


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
        for key, value in new_config.items():
            setattr(self, key, value)


class ComponentBase(ABC):
    """Base class for all components in the system."""
    def __init__(
        self,
        name: str,
        type_: str = "Base",
        config: ConfigBase = ConfigBase(),
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        process_function: Optional[callable] = lambda x: x,
        input_schema: SchemaID = ANY_SCHEMA,
        output_schema: SchemaID = ANY_SCHEMA
    ) -> None:

        self.name = name
        self.type_ = type_
        self.config = config
        self.input_schema, self.output_schema = input_schema, output_schema

        self.data_buffer = DataBuffer(
            mode=buffer_mode,
            size=buffer_size,
            process_function=process_function,
        )

    def __repr__(self) -> str:
        return f"<{self.type_}> {self.name}: {self.config}"

    def process(self, data):
        is_byte = False
        if isinstance(data, bytes):
            schema_id, data = deserialize(data)
            is_byte = True
            check_is_same_schema(schema_id, self.input_schema)

        data = self.data_buffer.add(data)

        return data if not is_byte else serialize(self.output_schema, data)

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: dict) -> None:
        self.config.update_config(new_config)
