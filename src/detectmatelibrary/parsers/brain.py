from detectmatelibrary.bases.base_parsers.parser_generator import ParserGeneratorConfig, ParserGenerator
from detectmateperformance.brain import Brain

from typing import Any, override

from pydantic import Field


class BrainConfig(ParserGeneratorConfig):
    method_type: str = Field(default="brain_parser", description="Indicates what type of method it is.")

    weight: float = Field(default=0.5, description="Weight value in Brain")

    Finetune: list[list[str | list[Any]]] = Field(
        default=[
            ["weight", [0.5, 1.0, 1.5]],
        ],
        description="fitting description yet to find",
    )


class BrainParser(ParserGenerator):
    def __init__(
        self,
        name: str = "BrainParser",
        config: BrainConfig | dict[str, Any] = BrainConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = BrainConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.parser_gen: Brain

    @override
    def init_parser(self, config: BrainConfig) -> Brain:  # type: ignore
        return Brain(weight=config.weight)
