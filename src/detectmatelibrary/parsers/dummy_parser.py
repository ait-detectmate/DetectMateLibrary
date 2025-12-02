from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from typing import Any


class DummyParserConfig(CoreParserConfig):
    """Configuration for DummyParser."""
    method_type: str = "dummy_parser"


class DummyParser(CoreParser):
    """A dummy parser for testing purposes."""

    def __init__(
        self,
        name: str = "DummyParser",
        config: DummyParserConfig | dict[str, Any] = DummyParserConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DummyParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        output_["EventID"] = 2
        output_["variables"].extend(["dummy_variable"])
        output_["template"] = "This is a dummy template"
