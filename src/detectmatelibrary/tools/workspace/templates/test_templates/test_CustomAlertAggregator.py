from ..CustomAlertAggregator import CustomAlertAggregator, CustomAlertAggregatorConfig
from detectmatelibrary.helper.from_to import From


default_args = {
    "alert_aggregators": {
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
        alert_aggregator = CustomAlertAggregator(name="CustomAlertAggregator", config=default_args)

        gen = From.json(alert_aggregator, "data.json", do_process=False)
        i = 0
        while True:
            try:
                data = next(gen)
            except StopIteration:
                break
            output = alert_aggregator.process(data)
            if i % 3 == 2:
                assert getattr(output, "description") == "Custom alert aggregation"
                assert getattr(output, "detectorIDs") == ["MyCoolThing"]*3
                assert getattr(output, "alertsObtain")["type"] == \
                       "Anomalies aggregated by CustomAlertAggregator"
                assert getattr(output, "detectorTypes") == ["MyCoolThing_detector"]*3
                assert getattr(output, "alertIDs") == [
                    f"MyCoolThing_{i + 8}", f"MyCoolThing_{i + 9}", f"MyCoolThing_{i + 10}"]
                assert getattr(output, "logIDs") == [str(i-2), str(i-1), str(i)]
            i += 1
