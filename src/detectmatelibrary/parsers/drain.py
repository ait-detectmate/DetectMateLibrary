from detectmatelibrary.bases.base_parsers.parser_generator import ParserGeneratorConfig, ParserGenerator
from detectmateperformance.drain import Drain

from typing import Any, override

from pydantic import Field


class DrainConfig(ParserGeneratorConfig):
    method_type: str = Field(default="drain_parser", description="Indicates what type of method it is.")

    depth: int = Field(default=2, description="fitting description yet to find")
    max_childs: int = Field(default=10, description="fitting description yet to find")
    sim_thres: float = Field(default=0.2, description="fitting description yet to find")

    Finetune: list[list[str | list[Any]]] = Field(
        default=[
            ["depth", [1, 2, 3, 4]],
            ["max_childs", [10, 40]],
            ["sim_thres", [0.2, 0.4, 0.6, 0.8]],
        ],
        description="fitting description yet to find",
    )


class DrainParser(ParserGenerator):
    def __init__(
        self,
        name: str = "DrainParser",
        config: DrainConfig | dict[str, Any] = DrainConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = DrainConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.parser_gen: Drain

    @override
    def init_parser(self, config: DrainConfig) -> Drain:  # type: ignore
        return Drain(
            depth=config.depth,
            max_child=config.max_childs,
            sim=config.sim_thres,
        )
