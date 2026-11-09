from detectmatelibrary.utils.log_format_utils import generate_logformat_regex
from detectmatelibrary.utils.log_format_utils import get_format_variables
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler
from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.common.core import CoreComponent, CoreConfig
from detectmatelibrary.utils.aux import get_timestamp
from detectmatelibrary import schemas

from pydantic import model_validator
from pydantic import Field

from typing_extensions import override
from typing import Any
import re


class CoreParserConfig(CoreConfig):
    component_type: str = Field(default="parsers", description="<$IGNORE$>")
    method_type: str = Field(default="core_parser", description="<$IGNORE$>")

    log_format: str | None = Field(
        default=None,
        description=("fitting description yet to find"),
    )
    time_format: str | None = Field(
        default=None,
        description=("fitting description yet to find"),
    )

    _regex: re.Pattern[str] | None = None

    log_source: str | None = Field(
        default=None, description="Process only inputs of the same log source."
    )

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
        config: CoreParserConfig | dict[str, Any] = CoreParserConfig(),
    ):
        if isinstance(config, dict):
            config = CoreParserConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.method_type,
            config=config,
            args_buffer=ArgsBuffer(mode=BufferMode.NO_BUF, size=None),
            input_schema=schemas.LogSchema,
            output_schema=schemas.ParserSchema,
        )
        self.time_format_handler = TimeFormatHandler()
        self.config: CoreParserConfig

    @override
    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:  # type: ignore
        var, content = get_format_variables(
            self.config._regex,
            log=input_["log"],
            time_format=self.config.time_format,
            time_format_handler=self.time_format_handler,
        )

        output_["parserID"] = self.name
        output_["parsedLogID"] = str(self.id_generator())
        output_["parserType"] = self.config.method_type
        output_["logID"] = input_["logID"]
        output_["log"] = input_["log"]
        output_["headerVariables"].update(var)
        input_["log"] = content

        output_["receivedTimestamp"] = get_timestamp()
        use_schema = self.parse(input_=input_, output_=output_)
        output_["parsedTimestamp"] = get_timestamp()

        return True if use_schema is None else use_schema

    @override
    def _is_input_eligible(self, data: schemas.LogSchema) -> bool:  # type: ignore
        return self.config.log_source is None or self.config.log_source == data["logSource"]

    def parse(
        self, input_: schemas.LogSchema, output_: schemas.ParserSchema
    ) -> bool | None:
        return True

    @override
    def train(self, input_: schemas.LogSchema) -> None:  # type: ignore
        pass

    @override
    def configure(self, input_: schemas.LogSchema,) -> None:  # type: ignore
        pass
