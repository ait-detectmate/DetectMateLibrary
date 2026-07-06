from detectmatelibrary.common.alert_aggregator import (
    CoreAlertAggregatorConfig, CoreAlertAggregator
)

from detectmatelibrary.schemas import DetectorSchema, OutputSchema

from typing import Any, Optional


class BasicConcatAggregationConfig(CoreAlertAggregatorConfig):
    method_type: str = "basic_concat_aggregator"
    buffer_size: int = 3


class BasicConcatAggregation(CoreAlertAggregator):
    def __init__(
        self,
        name: str = "BasicConcatAggregator",
        config: Optional[BasicConcatAggregationConfig | dict[str, Any]] = BasicConcatAggregationConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = BasicConcatAggregationConfig.from_dict(config, name)

        buffer_size: int = config.buffer_size  # type: ignore
        super().__init__(name=name, buffer_size=buffer_size, config=config)

    def aggregate_alerts(self, input_: list[DetectorSchema], output_: OutputSchema) -> bool:  # type: ignore
        output_["description"] = "Basic aggregation by alert concatenation"
        return True
