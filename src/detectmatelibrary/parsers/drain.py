from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.drain import Drain

from typing import Any


class DrainConfig(CoreParserConfig):
    method_type: str = "drain_parser"

    depth: int = 2
    max_childs: int = 10
    sim_thres: float = 0.2

    reset_in_post_train: bool = False


class DrainParser(CoreParser):
    def __init__(
        self,
        name: str = "DrainParser",
        config: DrainConfig | dict[str, Any] = DrainConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DrainConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.config: DrainConfig
        self.drain_gen = Drain(
            depth=self.config.depth,
            max_child=self.config.max_childs,
            sim=self.config.sim_thres,
        )
        self.tree_match: TreeMatcher | None = None

    def train(self, input_: schemas.LogSchema) -> None:  # type: ignore
        self.drain_gen.add(input_["log"])

    def post_train(self) -> None:
        self.tree_match = self.drain_gen.generate()
        if self.config.reset_in_post_train:
            self.drain_gen.reset()

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
