from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from detectmatelibrary.common._config import BasicConfig

from detectmatelibrary.schemas import BaseSchema

from typing import Any, Dict, Tuple, List


class SchemaPipeline:
    @staticmethod
    def preprocess(
        input_: BaseSchema, data: BaseSchema | bytes
    ) -> Tuple[bool, BaseSchema]:

        is_byte = False
        if isinstance(data, bytes):
            is_byte = True
            input_.deserialize(data)
            data = input_.copy()
        else:
            input_.check_is_same(data)
            data = data.copy()

        return is_byte, data

    @staticmethod
    def postprocess(
        data: BaseSchema, is_byte: bool
    ) -> BaseSchema | bytes:

        return data if not is_byte else data.serialize()


class CoreConfig(BasicConfig):
    start_id: int = 10
    data_use_training: int | None = None


def do_training(config: CoreConfig, index: int) -> bool:
    return config.data_use_training is not None and config.data_use_training > index


class CoreComponent:
    """Base class for all components in the system."""
    def __init__(
        self,
        name: str,
        type_: str = "Core",
        config: CoreConfig = CoreConfig(),
        args_buffer: ArgsBuffer = ArgsBuffer(BufferMode.NO_BUF),
        input_schema: type[BaseSchema] = BaseSchema,
        output_schema: type[BaseSchema] = BaseSchema
    ) -> None:

        self.name, self.type_, self.config = name, type_, config
        self.input_schema, self.output_schema = input_schema, output_schema

        self.data_buffer = DataBuffer(args_buffer)
        self.id_generator = SimpleIDGenerator(self.config.start_id)
        self.data_used_train = 0

    def __repr__(self) -> str:
        return f"<{self.type_}> {self.name}: {self.config}"

    def run(
        self, input_: List[BaseSchema] | BaseSchema, output_: BaseSchema
    ) -> bool:
        return False

    def train(
        self, input_: List[BaseSchema] | BaseSchema,
    ) -> None:
        pass

    def process(self, data: BaseSchema | bytes) -> BaseSchema | bytes | None:
        is_byte, data = SchemaPipeline.preprocess(self.input_schema(), data)
        if (data_buffered := self.data_buffer.add(data)) is None:  # type: ignore
            return None

        if do_training(config=self.config, index=self.data_used_train):
            self.data_used_train += 1
            self.train(input_=data_buffered)

        output_ = self.output_schema()
        anomaly_detected = self.run(input_=data_buffered, output_=output_)
        if not anomaly_detected:
            return None

        return SchemaPipeline.postprocess(output_, is_byte=is_byte)

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        self.config.update_config(new_config)
