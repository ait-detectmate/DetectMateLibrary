from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary.common._core_op._fed_component import FedOperations
from detectmatelibrary import schemas

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.types_ import LogTemplates
from detectmateperformance._iparser import IParser

from detectmatelibrary.utils.finetune import Combinations

from typing import Any, Callable, cast

from pydantic import Field
import msgpack


class ParserGeneratorConfig(CoreParserConfig):
    method_type: str = Field(default="gen_parser", description="Indicates what type of method it is.")

    reset_in_post_train: bool = Field(
        default=False, description="fitting description yet to find"
    )

    Finetune: list[list[str | list[Any]]] = Field(
        default=[],
        description="fitting description yet to find",
    )


def _found_ratio(logs: list[str], tree_matcher: TreeMatcher) -> float:
    results = tree_matcher.match_batch(logs).get_all_templates()

    score = 0.0
    for template in results:
        if "template not found" == template:
            score += 1.0

    return score / len(results)


def _get_best_config(
    logs: list[str],
    config: ParserGeneratorConfig,
    init_parser: Callable[[ParserGeneratorConfig], IParser],
) -> ParserGeneratorConfig:

    found_ratio: list[float] = []
    length: list[int] = []

    for config in (comb := Combinations(config))():  # type: ignore
        parser = init_parser(config)
        for input_ in logs:
            parser.add(input_)
        tree_matcher = parser.generate()

        found_ratio.append(_found_ratio(logs, tree_matcher))
        length.append(len(tree_matcher))

    n = max(length)
    for le, sc in zip(length, found_ratio):
        comb.add_value((float(le) / n) + sc)

    new_config: ParserGeneratorConfig = comb.get_best()  # type: ignore
    return new_config


class ParserGenerator(CoreParser):
    def __init__(
        self,
        name: str = "ParerGenerator",
        config: ParserGeneratorConfig | dict[str, Any] = ParserGeneratorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = ParserGeneratorConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self.config: ParserGeneratorConfig

        self.parser_gen = self.init_parser(config=config)
        self.tree_match: TreeMatcher | None = None

        self.config_buffer: list[str] = []

    # ---- Standard parser methods ----------------------------------
    def configure(self, input_: schemas.LogSchema) -> None:  # type: ignore
        self.config_buffer.append(input_["log"])

    def set_configuration(self) -> None:
        self.config = _get_best_config(
            self.config_buffer, config=self.config, init_parser=self.init_parser
        )
        self.config_buffer = []

    def train(self, input_: schemas.LogSchema) -> None:  # type: ignore
        self.parser_gen.add(input_["log"])

    def post_train(self) -> None:
        self.tree_match = self.parser_gen.generate()
        if self.config.reset_in_post_train:
            self.parser_gen.reset()

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> None:
        if self.tree_match is None:
            output_["eventID"] = -1
            output_["template"] = "templates not yet generated"
        else:
            parsed = self.tree_match.match_log(input_["log"], get_var=True)[0]

            output_["eventID"] = parsed["EventID"]
            output_["variables"].extend(parsed["ParamList"])
            output_["template"] = parsed["Template"]

    # ---- Methods only part of parser generator ----------------------------------
    def init_parser(self, config: ParserGeneratorConfig) -> IParser:
        """This method need to be update it in the child classes."""
        return IParser()

    def get_templates(self) -> list[str]:
        return self.tree_match.get_templates(False) if self.tree_match is not None else []

    def set_templates(self, templates: list[str]) -> None:
        self.tree_match = TreeMatcher(LogTemplates(templates))

    # ---- Federation methods ----------------------------------------------------
    def aggregate_strategy(self, components: set[FedOperations]) -> None:
        parsers = cast(set[ParserGenerator], components)
        templates = sorted({
            template for parser in parsers for template in parser.get_templates()
        })
        for parser in parsers:
            parser.set_templates(templates)

    def to_binary(self) -> bytes:
        templates = self.get_templates()
        if not templates:
            return b""
        binary: bytes = msgpack.packb(templates, use_bin_type=True)
        return binary

    def load_binary(self, binary: bytes) -> None:
        templates = msgpack.unpackb(binary, raw=False) if binary else []
        self.set_templates(templates)
