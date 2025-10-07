from src.components.common.core import CoreComponent, ConfigCore
from src.components.utils.data_buffer import ArgsBuffer
import src.components.utils.id_generator as op

import src.schemas as schemas

from abc import ABC, abstractmethod
from typing import Any, Optional


class CoreParserConfig(ConfigCore):
    parserType: str = "<PLACEHOLDER>"

    start_id: int = 0


def _generate_default_output(
    input_: schemas.LogSchema, config: CoreParserConfig
) -> schemas.ParserSchema:
    return schemas.initialize(
        schema_id=schemas.PARSER_SCHEMA,
        **{
            "__version__": "1.0.0",
            "parserType": config.parserType,
            "EventID": 0,
            "template": "",
            "parserID": 0,
            "logID": input_.logID,
            "log": input_.log,
        }
    )


class CoreParser(CoreComponent, ABC):
    def __init__(
        self,
        name: str = "CoreParser",
        config: Optional[CoreParserConfig | dict] = CoreParserConfig(),
        id_generator: op.SimpleIDGenerator = op.SimpleIDGenerator,
    ):
        if isinstance(config, dict):
            config = CoreParserConfig.from_dict(config)

        super().__init__(
            name=name,
            type_="Parser",
            config=config,
            train_function=self.train,
            process_function=self.run,
            args_buffer=ArgsBuffer(mode="no_buf", size=None),
            input_schema=schemas.LOG_SCHEMA,
            output_schema=schemas.PARSER_SCHEMA,
        )
        self.id_generator = id_generator(self.config.start_id)

    def run(self, input_: schemas.LogSchema) -> schemas.ParserSchema:
        output_ = _generate_default_output(input_=input_, config=self.config)

        self.parse(input_=input_, output_=output_)
        output_.parserID = self.id_generator()
        return output_

    @abstractmethod
    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> None:
        return

    def train(self, data: Any, config: ConfigCore) -> None:
        pass
