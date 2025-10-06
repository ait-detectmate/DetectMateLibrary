
from src.components.common.core import CoreComponent, ConfigCore
from src.components.common._op import LogIDGenerator
import src.schemas as schemas

from abc import ABC, abstractmethod
from typing import Optional


class ReaderConfig(ConfigCore):
    logSource: str = "<PLACEHOLDER>"
    hostname: str = "<PLACEHOLDER>"

    start_id: int = 0


class CoreReader(CoreComponent, ABC):
    def __init__(
        self,
        name: str,
        config: Optional[ReaderConfig | dict] = ReaderConfig(),
        id_generator: LogIDGenerator = LogIDGenerator,
    ) -> None:

        if isinstance(config, dict):
            config = ReaderConfig.from_dict(config)
        super().__init__(
            name=name, type_="Reader", config=config, output_schema=schemas.LOG_SCHEMA
        )

        self.data_buffer = None
        self.id_generator = id_generator(self.config.start_id)

    def __init_logs(self) -> schemas.SchemaT:
        return schemas.initialize(
            schema_id=self.output_schema,
            **{
                "__version__": "1.0.0",
                "logID": self.id_generator(),
                "log": "<PLACEHOLDER>",
                "logSource": self.config.logSource,
                "hostname": self.config.hostname,
            }
        )

    def process(self, as_bytes: bool = True) -> schemas.SchemaT | bytes | None:
        is_new_log = self.read(log := self.__init_logs())
        if not is_new_log:
            return None

        return schemas.serialize(self.output_schema, log) if as_bytes else log

    @abstractmethod
    def read(self, output_: schemas.SchemaT) -> bool:
        output_
