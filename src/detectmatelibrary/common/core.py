from detectmatelibrary.common._core_op._fit_logic import FitLogicState
from detectmatelibrary.common._core_op._schema_pipeline import SchemaPipeline
from detectmatelibrary.common._core_op._fit_logic import FitLogic

from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from detectmatelibrary.common._config import BasicConfig

from detectmatelibrary.schemas import BaseSchema

from tools.logging import logger, setup_logging

from typing import Any, Dict, List


setup_logging()


class CoreConfig(BasicConfig):
    start_id: int = 10
    data_use_training: int | None = None
    data_use_configure: int | None = None
    use_config_data_as_training: bool = False


class Component:
    """Empty methods."""
    def __init__(
        self,
        name: str,
        type_: str = "Core",
        config: CoreConfig = CoreConfig(),
    ) -> None:
        self.name, self.type_, self.config = name, type_, config

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

    def configure(
        self, input_: List[BaseSchema] | BaseSchema,
    ) -> None:
        pass

    def set_configuration(self) -> None:
        pass

    def post_train(self) -> None:
        pass

    def get_config(self) -> Dict[str, Any]:
        return self.config.get_config()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        self.config.update_config(new_config)


class CoreComponent(Component):
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
        super().__init__(name=name, type_=type_, config=config)
        self.input_schema, self.output_schema = input_schema, output_schema

        self.data_buffer = DataBuffer(args_buffer)
        self.id_generator = SimpleIDGenerator(self.config.start_id)
        self.fitlogic = FitLogic(
            data_use_configure=self.config.data_use_configure,
            data_use_training=self.config.data_use_training,
        )
        self.buffer_train: list[BaseSchema | list[BaseSchema]] = []

    def process(self, data: BaseSchema | bytes) -> BaseSchema | bytes | None:
        is_byte, data = SchemaPipeline.preprocess(self.input_schema(), data)
        logger.debug(f"<<{self.name}>> received:\n{data}")

        if (data_buffered := self.data_buffer.add(data)) is None:  # type: ignore
            return None

        if (fit_state := self.fitlogic.run()) == FitLogicState.DO_CONFIG:
            logger.debug(f"<<{self.name}>> use data for configuration")
            self.configure(input_=data_buffered)
            if self.config.use_config_data_as_training:
                self.buffer_train.append(data_buffered)
            return None
        elif self.fitlogic.finish_config():
            logger.debug(f"<<{self.name}>> finalizing configuration")
            self.set_configuration()
            if self.config.use_config_data_as_training:
                logger.debug(f"<<{self.name}>> Adding data from config to training")
                [self.train(input_) for input_ in self.buffer_train]

        if fit_state == FitLogicState.DO_TRAIN:
            logger.debug(f"<<{self.name}>> use data for training")
            self.train(input_=data_buffered)
        elif self.fitlogic.finish_training():
            logger.debug(f"<<{self.name}>> finalizing training")
            self.post_train()

        output_ = self.output_schema()
        logger.debug(f"<<{self.name}>> processing data")
        return_schema = self.run(input_=data_buffered, output_=output_)
        if not return_schema:
            logger.debug(f"<<{self.name}>> returns None")
            return None

        logger.debug(f"<<{self.name}>> processed:\n{output_}")
        return SchemaPipeline.postprocess(output_, is_byte=is_byte)
