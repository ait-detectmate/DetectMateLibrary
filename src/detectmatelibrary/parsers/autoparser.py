from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.auto_parser import AutoParse


from typing import Any


class AutoParserConfig(CoreParserConfig):
    method_type: str = "auto_parser"
    num_use: int = 10


class AutoParser(CoreParser):
    def __init__(
        self,
        name: str = "AutoParser",
        config: AutoParserConfig | dict[str, Any] = AutoParserConfig()
    ) -> None:

        if isinstance(config, dict):
            config = AutoParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.config: AutoParserConfig
        self.auto_gen = AutoParse(num_use=self.config.num_use)
        self.tree_match: TreeMatcher | None = None

        self.config_buffer: list[str] = []

    def train(self, input_: schemas.LogSchema) -> None:  # type: ignore
        self.auto_gen.add(input_["log"])

    def post_train(self) -> None:
        self.tree_match = self.auto_gen.generate()

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        if self.tree_match is None:
            output_["EventID"] = -1
            output_["template"] = "templates not yet generated"
        else:
            parsed = self.tree_match.match_log(input_["log"], get_var=True)[0]

            output_["EventID"] = parsed["EventID"]
            output_["variables"].extend(parsed["ParamList"])
            output_["template"] = parsed["Template"]
