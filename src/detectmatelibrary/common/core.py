from detectmatelibrary.common._core_op._fit_logic import FitLogicState, StatesL
from detectmatelibrary.common._core_op._schema_pipeline import SchemaPipeline
from detectmatelibrary.common._core_op._fit_logic import FitLogic

from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode
from detectmatelibrary.utils.id_generator import SimpleIDGenerator

from detectmatelibrary.common._config import BasicConfig

from detectmatelibrary.schemas import BaseSchema

from detectmatelibrary.tools.logging import logger, setup_logging

from detectmatelibrary.utils.persistency import EventPersistency
from detectmatelibrary.utils import persistency

from typing import Any, Dict, List, Protocol, Callable


setup_logging()

# Persistency ##################################################################


class _Stoppable(Protocol):
    """Structural type for objects ``Component`` will stop on context-manager
    exit.

    Decouples ``Component`` from any concrete saver implementation: a subclass
    may assign anything with a ``stop()`` method to ``self.saver`` (today the
    only such type is ``PersistencySaver``) without ``common.core`` having to
    import the persistency package. This preserves the dependency direction
    detectmate -> persistency, not the reverse.
    """
    def stop(self) -> None: ...


class PersistencyOp:
    @staticmethod
    def __get_persistency(instance: object) -> EventPersistency | None:
        ep = getattr(instance, "persistency", None)
        if ep is None:
            logger.debug("No persistency configured, nothing to export")
        return ep

    @staticmethod
    def __apply(
        instance: object,
        op: Callable[[EventPersistency, Any, dict[str, Any] | None], bytes | None],
        path: Any = None,
        storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:

        if (ep := PersistencyOp.__get_persistency(instance)) is None:
            return None

        saver = getattr(instance, "saver", None)
        if saver is not None:
            with saver.locked():
                return op(ep, path, storage_options)
        return op(ep, path, storage_options)

    @staticmethod
    def save(
        instance: object,
        path: str | None = None,
        storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:
        """Save this component's EventPersistency state.

        When path is None, returns the state as bytes (zip archive).
        When path is given, writes to that fsspec URI and returns None.
        Returns None if no persistency is configured. Thread-safe when a
        PersistencySaver is running: acquires the saver lock before saving
        (guards against the background save timer and concurrent ingest).
        """

        return PersistencyOp.__apply(
            instance=instance, path=path, storage_options=storage_options, op=persistency.save
        )

    @staticmethod
    def load(
        instance: object,
        path: str | bytes,
        storage_options: dict[str, Any] | None = None,
    ) -> None:
        """Restore this component's EventPersistency state.

        path may be an fsspec URI string or bytes returned by
        export_state(). No-op if no persistency is configured. Thread-safe
        when a PersistencySaver is running: acquires the saver lock before
        loading (guards against the background save timer).
        """

        PersistencyOp.__apply(
            instance=instance, path=path, storage_options=storage_options, op=persistency.load
        )


# Train operations ##################################################################

class TrainBuffer:
    def __init__(self) -> None:
        self.buffer: list[BaseSchema | list[BaseSchema]] = []

    def __len__(self) -> int:
        return len(self.buffer)

    def __add__(self, elem: BaseSchema | list[BaseSchema]) -> "TrainBuffer":
        self.buffer.append(elem)
        return self

    def __next__(self) -> BaseSchema | list[BaseSchema]:
        if len(self.buffer) == 0:
            raise StopIteration
        return self.buffer.pop(0)

    def __iter__(self) -> "TrainBuffer":
        return self


# Core component skeleton structure ################################################

class CoreConfig(BasicConfig):
    start_id: int = 10
    data_use_training: int | None = None
    data_use_configure: int | None = None
    use_config_data_as_training: bool = True


class Component:
    """Empty methods."""
    def __init__(
        self,
        name: str,
        type_: str = "Core",
        config: CoreConfig = CoreConfig(),
    ) -> None:
        self.name, self.type_, self.config = name, type_, config
        self.saver: _Stoppable | None = None

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

    def __enter__(self) -> "Component":
        return self

    def __exit__(self, *_: Any) -> None:
        if self.saver is not None:
            self.saver.stop()


# Core component ################################################

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
        self.buffer_train = TrainBuffer()

    def export_state(
        self, path: str | None = None, storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:
        return PersistencyOp.save(
            instance=self, path=path, storage_options=storage_options
        )

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        return PersistencyOp.load(
            instance=self, path=path, storage_options=storage_options
        )

    def update_state(self, state: StatesL) -> None:
        self.fitlogic.update_state(state)

    def get_state(self) -> str:
        return self.fitlogic.get_last_state()

    def get_window_size(self) -> int:
        return self.data_buffer.get_window_size()

    def process(self, data: BaseSchema | bytes) -> BaseSchema | bytes | None:
        is_byte, data = SchemaPipeline.preprocess(self.input_schema(), data)
        logger.debug(f"<<{self.name}>> received:\n{data}")

        if (data_buffered := self.data_buffer.add(data)) is None:  # type: ignore
            return None

        if (fit_state := self.fitlogic.run()) == FitLogicState.DO_CONFIG:
            logger.debug(f"<<{self.name}>> use data for configuration")
            self.configure(input_=data_buffered)
            if self.config.use_config_data_as_training:
                self.buffer_train + data_buffered
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
