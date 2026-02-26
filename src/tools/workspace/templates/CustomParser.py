from typing import Any

from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.helper.from_to import From
from detectmatelibrary import schemas


class CustomParserConfig(CoreParserConfig):
    """Configuration for CustomParser."""
    # You can change this to whatever method_type you need
    method_type: str = "custom_parser"


class CustomParser(CoreParser):
    """Template parser implementation based on CoreParser.

    Replace this docstring with a description of what your parser does.
    """

    def __init__(
        self,
        name: str = "CustomParser",
        config: CustomParserConfig | dict[str, Any] = CustomParserConfig(),
    ) -> None:
        # Allow passing either a config instance or a plain dict
        if isinstance(config, dict):
            config = CustomParserConfig.from_dict(config, name)

        super().__init__(name=name, config=config)

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema,
    ) -> None:
        """Parse a single log entry and populate the output schema.

        :param input_: Input log schema instance
        :param output_: Parser output schema instance to be mutated in-
            place
        """

        # Dummy implementation example (replace with real logic)
        output_["EventID"] = 2  # Number of the log template
        output_["variables"].extend(["dummy_variable"])  # Variables found in the log
        output_["template"] = "This is a dummy template"  # Log template


if __name__ == "__main__":

    print(parser := CustomParser())

    print("Running with data...")
    for parsed_log in From.json(parser, "data.json"):
        print(parsed_log)
