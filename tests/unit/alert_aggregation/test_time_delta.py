from detectmatelibrary.alert_aggregation.time_delta import (
    TimeDeltaAggregation,
    TimeDeltaAggregationConfig,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema


def make_alert(alert_id: str, timestamp: int) -> DetectorSchema:
    return DetectorSchema(
        {
            "detectorID": "detector",
            "detectorType": "dummy",
            "alertID": alert_id,
            "detectedTimestamp": timestamp,
            "logIDs": [f"log-{alert_id}"],
            "score": 0.0,
            "logTimestamps": [timestamp],
            "description": "test alert",
            "receivedTimestamp": timestamp,
            "alertDetails": {},
        }
    )


def create_aggregator(*, delta: float = 10.0) -> TimeDeltaAggregation:
    return TimeDeltaAggregation(
        config=TimeDeltaAggregationConfig(buffer_size=3, delta=delta)
    )


class TestTimeDeltaAggregation:
    def test_default_configuration(self) -> None:
        config = TimeDeltaAggregationConfig()

        assert config.method_type == "time_delta_aggregator"
        assert config.delta == 10.0

    def test_single_metric_returns_absolute_timestamp_delta(self) -> None:
        aggregator = create_aggregator()
        first = make_alert("first", 100)
        second = make_alert("second", 93)

        assert aggregator.single_metric(first, second) == 7.0
        assert aggregator.single_metric(second, first) == 7.0

    def test_single_metric_uses_last_extracted_timestamp(self) -> None:
        aggregator = create_aggregator()
        first = make_alert("first", 100)
        second = make_alert("second", 106)
        first["logTimestamps"] = [90, 100]
        second["logTimestamps"] = [101, 106]

        assert aggregator.single_metric(first, second) == 6.0

    def test_discard_alert_fn_keeps_only_latest_alert(self) -> None:
        aggregator = create_aggregator()
        alerts = [
            make_alert("first", 1),
            make_alert("second", 2),
            make_alert("third", 3),
        ]

        assert aggregator.discard_alert_fn(alerts) == [True, True, False]

    def test_alerts_within_delta_are_assigned_to_same_group(self) -> None:
        aggregator = create_aggregator(delta=10.0)
        first_output = AggregateSchema()
        second_output = AggregateSchema()

        assert aggregator.aggregate_alerts(make_alert("first", 100), first_output)
        assert aggregator.aggregate_alerts(make_alert("second", 110), second_output)

        assert first_output["alertDetails"]["first"] == "0"
        assert second_output["alertDetails"]["second"] == "0"
        assert second_output["description"] == (
            "Alert aggregation by the time-delta method."
        )

    def test_alerts_outside_delta_are_assigned_to_different_groups(self) -> None:
        aggregator = create_aggregator(delta=10.0)
        aggregator.aggregate_alerts(make_alert("first", 100), AggregateSchema())
        second_output = AggregateSchema()

        assert aggregator.aggregate_alerts(make_alert("second", 111), second_output)

        assert second_output["alertDetails"]["second"] == "1"

    def test_only_latest_alert_remains_relevant_after_aggregation(self) -> None:
        aggregator = create_aggregator()
        aggregator.aggregate_alerts(make_alert("first", 100), AggregateSchema())
        aggregator.aggregate_alerts(make_alert("second", 105), AggregateSchema())

        assert [alert["alertID"] for alert in aggregator.relevant_alerts] == ["second"]
