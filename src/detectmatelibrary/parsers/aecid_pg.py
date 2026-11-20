from detectmatelibrary.bases.base_parsers import ParserGenerator, ParserGeneratorConfig
from detectmateperformance.aecid_pg import AECID_PG

from typing import Any, override

from pydantic import Field


class AECIDPGConfig(ParserGeneratorConfig):
    method_type: str = Field(
        default="aecid_pg_parser", description="Indicates what type of method it is."
    )

    theta_1: float = Field(
        default=0.2, description="Minimum relative branch frequency for a branch to count as common."
    )
    theta_2: float = Field(
        default=0.8,
        description=(
            "Merge branches below this frequency when the combined frequency "
            "of common branches is below theta_3."
        ),
    )
    theta_3: float = Field(
        default=0.5,
        description="Minimum combined frequency of common branches needed to merge the remaining branches.",
    )

    Finetune: list[list[str | list[Any]]] = Field(
        default=[
            ["theta_1", [0.01, 0.05, 0.1, 0.2]],
            ["theta_2", [0.7, 0.8, 0.9]],
            ["theta_3", [0.4, 0.5, 0.6]],
        ],
        description="Candidate [parameter, values] pairs for automatic configuration.",
    )


class AECIDPGParser(ParserGenerator):
    def __init__(
        self,
        name: str = "AECIDPGParser",
        config: AECIDPGConfig | dict[str, Any] = AECIDPGConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = AECIDPGConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.parser_gen: AECID_PG

    @override
    def init_parser(self, config: AECIDPGConfig) -> AECID_PG:  # type: ignore
        return AECID_PG(
            theta_1=config.theta_1,
            theta_2=config.theta_2,
            theta_3=config.theta_3,
        )
