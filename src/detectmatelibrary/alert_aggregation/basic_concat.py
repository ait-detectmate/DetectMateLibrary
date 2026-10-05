from detectmatelibrary.common.alert_aggregator import (CoreAlertAggregatorConfig, CoreAlertAggregator)
from detectmatelibrary.schemas import DetectorSchema, AggregateSchema
from typing import Any, Optional


class BasicConcatAggregationConfig(CoreAlertAggregatorConfig):
    method_type: str = "basic_concat_aggregator"
    buffer_size: int = 3
    deduplicate_values: bool = False


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
            output_["extractedTimestamps"] = list(dict.fromkeys(output_["extractedTimestamps"]))
        return True
