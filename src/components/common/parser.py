from components.common.core import CoreComponent, CoreConfig

from utils.data_buffer import ArgsBuffer

import schemas as schemas

from typing import Any, Optional


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

    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> None:

        output_.parsedLogID = self.id_generator()
        output_.logID = input_.logID
        output_.log = input_.log

        self.parse(input_=input_, output_=output_)
        return output_

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> None:
        return

    def train(self, data: Any, config: CoreConfig) -> None:
        pass
