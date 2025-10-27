from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from detectmatelibrary.common._config import BasicConfig

from detectmatelibrary import schemas

from typing import Any, Dict, Tuple, List


class SchemaPipeline:
    @staticmethod
    def preprocess(
        schema_id: schemas.SchemaID, data: schemas.AnySchema | bytes
    ) -> Tuple[bool, schemas.AnySchema]:

        is_byte = False
        if isinstance(data, bytes):
            schema_id_, data = schemas.deserialize(data)
            is_byte = True
            schemas.check_is_same_schema(schema_id_, schema_id)

        return is_byte, schemas.copy(schema_id, schema=data)

    @staticmethod
    def postprocess(
        schema_id: schemas.SchemaID, data: schemas.AnySchema, is_byte: bool
    ) -> schemas.AnySchema | bytes:

        schemas.check_if_schema_is_complete(data)
        return data if not is_byte else schemas.serialize(schema_id, data)


class CoreConfig(BasicConfig):
    start_id: int = 10
    data_use_training: int | None = None


class CoreComponent:
    """Base class for all components in the system."""
    def __init__(
        self,
        name: str,
        type_: str = "Core",
        config: CoreConfig = CoreConfig(),
        args_buffer: ArgsBuffer = ArgsBuffer("no_buf"),
        input_schema: schemas.SchemaID = schemas.BASE_SCHEMA,
        output_schema: schemas.SchemaID = schemas.BASE_SCHEMA
    ) -> None:

        self.name, self.type_, self.config = name, type_, config
        self.input_schema, self.output_schema = input_schema, output_schema

        self.data_buffer = DataBuffer(args_buffer)
        self.id_generator = SimpleIDGenerator(self.config.start_id)
        self.data_used_train = 0

    def __repr__(self) -> str:
        return f"<{self.type_}> {self.name}: {self.config}"

    def run(
        self, input_: List[schemas.AnySchema] | schemas.AnySchema, output_: schemas.AnySchema
    ) -> None:
        pass

    def train(
        self, input_: List[schemas.AnySchema] | schemas.AnySchema,
    ) -> None:
        pass

    def process(self, data: schemas.AnySchema | bytes) -> schemas.AnySchema | bytes | None:
        is_byte, data = SchemaPipeline.preprocess(self.input_schema, data)
        if (data_buffered := self.data_buffer.add(data)) is None:
            return None

        if self.config.data_use_training is not None and self.config.data_use_training > self.data_used_train:
            self.data_used_train += 1
            self.train(input_=data_buffered)

        output_ = schemas.initialize_with_default(self.output_schema, config=self.config)
        anomaly_detected = self.run(input_=data_buffered, output_=output_)
        if not anomaly_detected:
            return None

        return SchemaPipeline.postprocess(self.output_schema, output_, is_byte=is_byte)

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: dict) -> None:
        self.config.update_config(new_config)
