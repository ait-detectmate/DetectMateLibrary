from detectmatelibrary.common.alert_aggregator import (CoreAlertAggregatorConfig, CoreAlertAggregator)
from detectmatelibrary.schemas import DetectorSchema, AggregateSchema
from detectmatelibrary.helper.from_to import From

from typing import Any


class CustomAlertAggregatorConfig(CoreAlertAggregatorConfig):
    method_type: str = "custom_alert_aggregator"
    buffer_size: int = 3


class CustomAlertAggregator(CoreAlertAggregator):
    def __init__(
        self,
        name: str = "CustomAlertAggregator",
        config: CustomAlertAggregatorConfig | dict[str, Any] = CustomAlertAggregatorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CustomAlertAggregatorConfig.from_dict(config, name)
        buffer_size: int = config.buffer_size
        super().__init__(name=name, buffer_size=buffer_size, config=config)

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:
        output_["description"] = "Custom alert aggregation"
        output_["alertDetails"]["type"] = "Anomalies aggregated by CustomAlertAggregator"
        return True


if __name__ == "__main__":
    print(aggregator := CustomAlertAggregator())
    print("Running with data...")
    for alerts in From.json(aggregator, "data.json"):
        print(alerts)
