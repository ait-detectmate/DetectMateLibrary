from detectmatelibrary.common.core import CoreComponent, CoreConfig, SchemaPipeline

from detectmatelibrary import schemas

from typing import Optional, Any


class CoreReaderConfig(CoreConfig):
    comp_type: str = "readers"
    method_type: str = "core_reader"

    logSource: str = "<PLACEHOLDER>"
    hostname: str = "<PLACEHOLDER>"


class CoreReader(CoreComponent):
    def __init__(
        self,
        name: str = "CoreReader",
        config: Optional[CoreReaderConfig | dict[str, Any]] = CoreReaderConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = CoreReaderConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.method_type,  # type: ignore
            config=config,  # type: ignore
            output_schema=schemas.LogSchema
        )
        self.config: CoreReaderConfig

        del self.data_buffer

    def __init_logs(self) -> schemas.LogSchema:
        return self.output_schema({  # type: ignore
                "__version__": "1.0.0",
                "logID": self.id_generator(),
                "logSource": self.config.logSource,
                "hostname": self.config.hostname,
        })

    def process(self, as_bytes: bool = True) -> schemas.LogSchema | bytes | None:  # type: ignore
        is_new_log = self.read(log := self.__init_logs())
        if not is_new_log:
            return None

        return SchemaPipeline.postprocess(log, is_byte=as_bytes) if is_new_log else None  # type: ignore

    def read(self, output_: schemas.LogSchema) -> bool:
        return False
