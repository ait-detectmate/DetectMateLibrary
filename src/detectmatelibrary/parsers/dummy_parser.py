from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas


class DummyParserConfig(CoreParserConfig):
    """Configuration for DummyParser."""
    pass


class DummyParser(CoreParser):
    """A dummy parser for testing purposes."""

    def __init__(
        self,
        name: str = "DummyParser",
        config: DummyParserConfig | dict = DummyParserConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DummyParserConfig.from_dict(config)
        super().__init__(name=name, config=config)

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:
        output_.EventID = 2
        output_.parserType = "DummyParser"
        output_.log = input_.log
        output_.variables.extend(["dummy_variable"])
        output_.template = "This is a dummy template"
        output_.logFormatVariables["timestamp"] = "0"
