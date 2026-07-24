from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.drain import Drain

from detectmatelibrary.utils.finetune import Combinations

from typing import Any


class DrainConfig(CoreParserConfig):
    method_type: str = "drain_parser"

    depth: int = 2
    max_childs: int = 10
    sim_thres: float = 0.2

    reset_in_post_train: bool = False

    finetune: list[list[str | list[Any]]] = [
        ["depth", [1, 2, 3, 4]],
        ["max_childs", [10, 40]],
        ["sim_thres", [0.2, 0.4, 0.6, 0.8]]
    ]


def _init_drain(config: DrainConfig) -> Drain:
    return Drain(
        depth=config.depth, max_child=config.max_childs, sim=config.sim_thres,
    )


def _found_ratio(logs: list[str], tree_matcher: TreeMatcher) -> float:
    results = tree_matcher.match_batch(logs).get_all_templates()
    print(results)

    score = 0.0
    for template in results:
        if "template not found" == template:
            score += 1.

    return score / len(results)


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
        self.drain_gen = _init_drain(config=config)
        self.tree_match: TreeMatcher | None = None

        self.config_buffer: list[str] = []

    def configure(self, input_: schemas.LogSchema) -> None:  # type: ignore
        self.config_buffer.append(input_["log"])

    def set_configuration(self) -> None:
        found_ratio: list[float] = []
        length: list[int] = []
        for config in (comb := Combinations(self.config))():
            drain = _init_drain(config)  # type: ignore
            for input_ in self.config_buffer:
                drain.add(input_)
            tree_matcher = drain.generate()

            found_ratio.append(_found_ratio(self.config_buffer, tree_matcher))
            length.append(len(tree_matcher))

        n = max(length)
        for le, sc in zip(length, found_ratio):
            comb.add_value((float(le) / n) + sc)

        self.config = comb.get_best()  # type: ignore

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
