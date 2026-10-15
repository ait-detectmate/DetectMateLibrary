from detectmatelibrary.common.alert_aggregator import (CoreAlertAggregatorConfig, CoreAlertAggregator)
from detectmatelibrary.schemas import DetectorSchema, AggregateSchema
from typing import Any, Optional
from pydantic import Field


class BasicConcatAggregationConfig(CoreAlertAggregatorConfig):
    method_type: str = Field(
        default="basic_concat_aggregator", description="Indicates what type of method it is."
    )
    buffer_size: int = Field(
        default=3,
        description="Number of most recent alerts aggregated together (size of the sliding window).",
    )
    deduplicate_values: bool = Field(
        default=False,
        description="Drop repeated entries from the aggregated ID, type and timestamp lists, "
        "keeping the first of each.",
    )


class BasicConcatAggregation(CoreAlertAggregator):
    def __init__(
        self,
        name: str = "BasicConcatAggregator",
        config: Optional[BasicConcatAggregationConfig | dict[str, Any]] = BasicConcatAggregationConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = BasicConcatAggregationConfig.from_dict(config, name)
        buffer_size: int = config.buffer_size  # type: ignore
        self.deduplicate_values: bool = config.deduplicate_values  # type: ignore
        super().__init__(name=name, buffer_size=buffer_size, config=config)

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:
        output_["description"] = "Basic aggregation by alert concatenation"
        if self.deduplicate_values:
            output_["detectorIDs"] = list(dict.fromkeys(output_["detectorIDs"]))
            output_["detectorTypes"] = list(dict.fromkeys(output_["detectorTypes"]))
            output_["alertIDs"] = list(dict.fromkeys(output_["alertIDs"]))
            output_["logIDs"] = list(dict.fromkeys(output_["logIDs"]))
            output_["logTimestamps"] = list(dict.fromkeys(output_["logTimestamps"]))
        return True
