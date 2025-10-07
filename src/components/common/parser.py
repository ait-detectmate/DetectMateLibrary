from src.components.common.core import CoreComponent, CoreConfig

from src.utils.data_buffer import ArgsBuffer

import src.schemas as schemas

from typing import Any, Optional


class CoreParserConfig(CoreConfig):
    parserType: str = "<PLACEHOLDER>"


def _generate_default_output(
    input_: schemas.LogSchema, config: CoreParserConfig
) -> schemas.ParserSchema:
    return schemas.initialize(
        schema_id=schemas.PARSER_SCHEMA,
        **{
            "__version__": "1.0.0",
            "parserType": config.parserType,
            "logID": input_.logID,
            "log": input_.log,
        }
    )


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

        output_.parserID = self.id_generator()
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
