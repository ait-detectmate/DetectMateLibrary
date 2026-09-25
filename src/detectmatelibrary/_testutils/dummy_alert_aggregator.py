from detectmatelibrary.common.alert_aggregator import (CoreAlertAggregatorConfig, CoreAlertAggregator)
from detectmatelibrary.schemas import DetectorSchema, AggregateSchema
from typing import Any, Optional


class DummyAlertAggregatorConfig(CoreAlertAggregatorConfig):
    method_type: str = "dummy_alert_aggregator"
    buffer_size: int = 3


class DummyAlertAggregator(CoreAlertAggregator):
    def __init__(
        self,
        name: str = "DummyAlertAggregator",
        config: Optional[DummyAlertAggregatorConfig | dict[str, Any]] = DummyAlertAggregatorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = DummyAlertAggregatorConfig.from_dict(config, name)
        buffer_size: int = config.buffer_size  # type: ignore
        super().__init__(name=name, buffer_size=buffer_size, config=config)

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema  # type: ignore
    ) -> bool:
        output_["description"] = "Dummy alert aggregation"
        output_["alertsObtain"]["type"] = "Anomalies aggregated by DummyAlertAggregator"
        return True
