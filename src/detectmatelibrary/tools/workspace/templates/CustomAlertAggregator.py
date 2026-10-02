from detectmatelibrary.common.alert_aggregator import (CoreAlertAggregatorConfig, CoreAlertAggregator)
from detectmatelibrary.schemas import DetectorSchema, AggregateSchema
from typing import Any, Optional
from detectmatelibrary.helper.from_to import From


class CustomAlertAggregatorConfig(CoreAlertAggregatorConfig):
    method_type: str = "custom_alert_aggregator"
    buffer_size: int = 3


class CustomAlertAggregator(CoreAlertAggregator):
    def __init__(
        self,
        name: str = "CustomAlertAggregator",
        config: Optional[CustomAlertAggregatorConfig | dict[str, Any]] = CustomAlertAggregatorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CustomAlertAggregatorConfig.from_dict(config, name)
        buffer_size: int = config.buffer_size  # type: ignore
        super().__init__(name=name, buffer_size=buffer_size, config=config)

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:
        output_["description"] = "Custom alert aggregation"
        output_["alertsObtain"]["type"] = "Anomalies aggregated by CustomAlertAggregator"
        return True


if __name__ == "__main__":
    print(aggregator := CustomAlertAggregator())
    print("Running with data...")
    for alerts in From.json(aggregator, "data.json"):
        print(alerts)
