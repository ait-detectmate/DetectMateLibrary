from ..common.core import CoreComponent, CoreConfig, SchemaPipeline

from .. import schemas

from typing import Optional


class CoreReaderConfig(CoreConfig):
    logSource: str = "<PLACEHOLDER>"
    hostname: str = "<PLACEHOLDER>"


class CoreReader(CoreComponent):
    def __init__(
        self,
        name: str,
        config: Optional[CoreReaderConfig | dict] = CoreReaderConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = CoreReaderConfig.from_dict(config)

        super().__init__(
            name=name, type_="Reader", config=config, output_schema=schemas.LOG_SCHEMA
        )

        self.data_buffer = None

    def __init_logs(self) -> schemas.SchemaT:
        return schemas.initialize(
            schema_id=self.output_schema,
            **{
                "__version__": "1.0.0",
                "logID": self.id_generator(),
                "logSource": self.config.logSource,
                "hostname": self.config.hostname,
            }
        )

    def process(self, as_bytes: bool = True) -> schemas.SchemaT | bytes | None:
        is_new_log = self.read(log := self.__init_logs())
        if not is_new_log:
            return None

        return SchemaPipeline.postprocess(self.output_schema, log, is_byte=as_bytes)

    def read(self, output_: schemas.SchemaT) -> bool:
        return False
