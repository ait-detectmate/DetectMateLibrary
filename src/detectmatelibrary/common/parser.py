from detectmatelibrary.common.core import CoreComponent, CoreConfig
from detectmatelibrary.common.config.parser import CoreParserConfig
from detectmatelibrary.utils.data_buffer import ArgsBuffer
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary import schemas

from typing import Any, Optional, Tuple
from datetime import datetime
import re


def _apply_time_format(time_str: str, time_format: str) -> str:
    try:
        dt = datetime.strptime(time_str, time_format)
        return str(int(dt.timestamp()))
    except Exception:
        return "0"


def _get_format_variables(pattern: str, time_format: str, log: str) -> Tuple[dict[str, str], str]:
    if not pattern:
        vars = {"timestamp": "0"}
    else:
        pattern = re.compile(pattern)
        match = pattern.search(log)
        vars = match.groupdict() if match else {"timestamp": "0"}

    if "timestamp" in vars and time_format:
        vars["timestamp"] = _apply_time_format(vars["timestamp"], time_format)
    return vars, log


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
        var, content = _get_format_variables(
            self.config.pattern, log=input_.log, time_format=self.config.time_format
        )

        output_.parsedLogID = self.id_generator()
        output_.parserType = self.config.parserType
        output_.logID = input_.logID
        output_.log = content
        output_.logFormatVariables.update(var)

        output_.receivedTimestamp = get_timestamp()
        use_schema = self.parse(input_=input_, output_=output_)
        output_.parsedTimestamp = get_timestamp()

        return True if use_schema is None else use_schema

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> bool:
        return True

    def train(self, data: Any, config: CoreConfig) -> None:
        pass
