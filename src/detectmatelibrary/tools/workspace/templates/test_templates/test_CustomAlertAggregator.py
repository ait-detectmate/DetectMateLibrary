from typing import Any
from detectmatelibrary import schemas
from ..CustomAlertAggregator import CustomAlertAggregator, CustomAlertAggregatorConfig


default_args = {
    "alert_aggregator": {
        "CustomAlertAggregator": {
            "method_type": "custom_alert_aggregator",
            "auto_config": False,
            "params": {},
        }
    }
}


class TestCustomAlertAggregator:
    def test_initialize_default(self) -> None:
        alert_aggregator = CustomAlertAggregator(name="CustomAlertAggregator", config=default_args)
        assert isinstance(alert_aggregator, CustomAlertAggregator)
        assert alert_aggregator.name == "CustomAlertAggregator"
        assert isinstance(alert_aggregator.config, CustomAlertAggregatorConfig)

    def test_run_aggregate_alerts_method(self) -> None:
        alert_aggregator = CustomAlertAggregator()
        data = schemas.DetectorSchema({"log": "test log"})
        output: Any = schemas.AggregateSchema()

        result = alert_aggregator.aggregate_alerts(data, output)

        assert output.description == "Dummy alert aggregation process"
        if result:
            assert output.score == 1.0
            assert "Anomaly detected" in output.alertsObtain["type"]
        else:
            assert output.score == 0.0
            assert len(output.alertsObtain) == 0
