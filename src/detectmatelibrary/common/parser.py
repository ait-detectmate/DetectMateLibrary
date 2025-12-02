from detectmatelibrary.utils.log_format_utils import generate_logformat_regex
from detectmatelibrary.utils.log_format_utils import get_format_variables
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler
from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.common.core import CoreComponent, CoreConfig
from detectmatelibrary.utils.aux import get_timestamp
from detectmatelibrary import schemas

from typing import Any, Optional, cast
from pydantic import model_validator
import re


class CoreParserConfig(CoreConfig):
    comp_type: str = "parsers"
    method_type: str = "core_parser"

    log_format: str | None = None
    time_format: str | None = None

    _regex: re.Pattern[str] | None = None

    # generate regex from log_format
    @model_validator(mode="after")
    def generate_regex(self) -> "CoreParserConfig":
        if self.log_format is not None:
            headers, regex = generate_logformat_regex(self.log_format)
            self._regex = regex
            self._headers = headers
        else:
            self._regex = None
            self._headers = []
        return self


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
            config=config,  # type: ignore
            args_buffer=ArgsBuffer(mode=BufferMode.NO_BUF, size=None),
            input_schema=schemas.LogSchema,
            output_schema=schemas.ParserSchema,
        )
        self.time_format_handler = TimeFormatHandler()

    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:  # type: ignore
        config = cast(CoreParserConfig, self.config)
        var, content = get_format_variables(
            config._regex,
            log=input_["log"],
            time_format=config.time_format,
            time_format_handler=self.time_format_handler
        )

        output_["parserID"] = self.name
        output_["parsedLogID"] = self.id_generator()
        output_["parserType"] = self.config.method_type
        output_["logID"] = input_["logID"]
        output_["log"] = input_["log"]
        output_["logFormatVariables"].update(var)
        input_["log"] = content

        output_["receivedTimestamp"] = get_timestamp()
        use_schema = self.parse(input_=input_, output_=output_)
        output_["parsedTimestamp"] = get_timestamp()

        return True if use_schema is None else use_schema

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> bool | None:
        return True

    def train(self, input_: schemas.LogSchema) -> None:  # type: ignore
        pass
