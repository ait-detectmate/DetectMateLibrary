from src.components.common.core import CoreComponent, CoreConfig

from src.utils.data_buffer import ArgsBuffer

import src.schemas as schemas

from typing import Any, Optional
from datetime import datetime


class CoreParserConfig(CoreConfig):
    parserType: str = "<PLACEHOLDER>"
    parserID: str = "<PLACEHOLDER>"


class CoreParser(CoreComponent):
    def __init__(
        self,
        name: str = "CoreParser",
        config: Optional[CoreParserConfig | dict] = CoreParserConfig(),
    ):
        if isinstance(config, dict):
            config = CoreParserConfig.from_dict(config)

        super().__init__(
            name=name,
            type_="Parser",
            config=config,
            args_buffer=ArgsBuffer(mode="no_buf", size=None),
            input_schema=schemas.LOG_SCHEMA,
            output_schema=schemas.PARSER_SCHEMA,
        )

    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:

        output_.parsedLogID = self.id_generator()
        output_.logID = input_.logID
        output_.log = input_.log
        output_.receivedTimestamp = int(datetime.now().timestamp())

        use_schema = self.parse(input_=input_, output_=output_)
        output_.parsedTimestamp = int(datetime.now().timestamp())

        return True if use_schema is None else use_schema

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> bool:
        return True

    def train(self, data: Any, config: CoreConfig) -> None:
        pass
