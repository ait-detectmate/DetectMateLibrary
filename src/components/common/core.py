from src.components.utils.aux import BasicConfig
from src.components.utils.data_buffer import DataBuffer, ArgsBuffer
from src.components.utils.id_generator import SimpleIDGenerator

import src.schemas as schemas

from typing import Callable, Optional, Any, Dict


class CoreConfig(BasicConfig):
    start_id: int = 0


class CoreComponent:
    """Base class for all components in the system."""
    def __init__(
        self,
        name: str,
        type_: str = "Core",
        config: CoreConfig = CoreConfig(),
        train_function: Optional[Callable[[Any], None]] = lambda x: None,
        process_function: Optional[Callable[[Any], Any]] = lambda x: x,
        args_buffer: ArgsBuffer = ArgsBuffer("no_buf"),
        input_schema: schemas.SchemaID = schemas.BASE_SCHEMA,
        output_schema: schemas.SchemaID = schemas.BASE_SCHEMA
    ) -> None:

        self.name = name
        self.type_ = type_
        self.config = config
        self.train = train_function
        self.processing_function = process_function
        self.input_schema, self.output_schema = input_schema, output_schema

        self.data_buffer = DataBuffer(args_buffer)
        self.id_generator = SimpleIDGenerator(self.config.start_id)

    def __repr__(self) -> str:
        return f"<{self.type_}> {self.name}: {self.config}"

    def process(
        self, data: schemas.AnySchema | bytes, learnmode: bool = False
    ) -> schemas.AnySchema | bytes | None:
        is_byte = False
        if isinstance(data, bytes):
            schema_id, data = schemas.deserialize(data)
            is_byte = True
            schemas.check_is_same_schema(schema_id, self.input_schema)

        data_buffered = self.data_buffer.add(data)
        if learnmode:
            result = self.train(data_buffered)  # returns None
        else:
            result = self.processing_function(data_buffered)
        if result is None:
            return None

        return result if not is_byte else schemas.serialize(self.output_schema, result)

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: dict) -> None:
        self.config.update_config(new_config)
