from detectmatelibrary.common.core import CoreComponent, CoreConfig
from detectmatelibrary.utils.data_buffer import ArgsBuffer
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.utils.data_buffer import BufferMode

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


def _get_format_variables(
    pattern: str | None, time_format: str, log: str
) -> Tuple[dict[str, str], str]:

    if pattern is None:
        vars = {"timestamp": "0"}
    else:
        cpattern = re.compile(pattern)
        match = cpattern.search(log)
        vars = match.groupdict() if match else {"timestamp": "0"}

    if "timestamp" in vars and time_format:
        vars["timestamp"] = _apply_time_format(vars["timestamp"], time_format)

    return vars, vars["content"] if "content" in vars else log


class CoreParserConfig(CoreConfig):
    comp_type: str = "parsers"
    method_type: str = "core_parser"

    pattern: str | None = None
    time_format: str | None = None


class CoreParser(CoreComponent):
    def __init__(
        self,
        name: str = "CoreParser",
        config: Optional[CoreParserConfig | dict[str, Any]] = CoreParserConfig(),
    ):
        if isinstance(config, dict):
            config = CoreParserConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.method_type,  # type: ignore
            config=config,   # type: ignore
            args_buffer=ArgsBuffer(mode=BufferMode.NO_BUFF, size=None),
            input_schema=schemas.LOG_SCHEMA,  # type: ignore
            output_schema=schemas.PARSER_SCHEMA,  # type: ignore
        )

    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        var, content = _get_format_variables(
            self.config.pattern, log=input_.log, time_format=self.config.time_format   # type: ignore
        )

        output_.parserID = self.name
        output_.parsedLogID = self.id_generator()
        output_.parserType = self.config.method_type
        output_.logID = input_.logID
        output_.log = input_.log
        output_.logFormatVariables.update(var)
        input_.log = content

        output_.receivedTimestamp = get_timestamp()
        use_schema = self.parse(input_=input_, output_=output_)
        output_.parsedTimestamp = get_timestamp()

        return True if use_schema is None else use_schema

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> bool | None:
        return True

    def train(self, input_: schemas.LogSchema) -> None:
        pass
