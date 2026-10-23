import pytest

from detectmatelibrary.alert_aggregation.density_clustering import (
    DensityClusteringAggregation,
    DensityClusteringAggregationConfig,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema
from detectmatelibrary.utils.data_buffer import BufferMode


def make_alert(alert_id: str, score: float) -> DetectorSchema:
    return DetectorSchema(
        {
            "detectorID": "detector",
            "detectorType": "dummy",
            "alertID": alert_id,
            "detectedTimestamp": 0,
            "logIDs": [f"log-{alert_id}"],
            "score": score,
            "logTimestamps": [0],
            "description": "test alert",
            "receivedTimestamp": 0,
            "alertDetails": {},
        }
    )


class ConcreteDensityClusteringAggregation(DensityClusteringAggregation):
    def single_metric(self, alert1: DetectorSchema, alert2: DetectorSchema) -> float:
        return abs(alert1["score"] - alert2["score"])

    def discard_alert_fn(self, alerts: list[DetectorSchema]) -> list[bool]:
        return [alert["alertID"].startswith("discard") for alert in alerts]


def create_aggregator(
    *,
    buffer_mode: BufferMode = BufferMode.BATCH,
    buffer_size: int = 3,
    delta: float = 1.0,
) -> ConcreteDensityClusteringAggregation:
    return ConcreteDensityClusteringAggregation(
        config=DensityClusteringAggregationConfig(
            buffer_mode=buffer_mode,
            buffer_size=buffer_size,
            delta=delta,
        )
    )


class TestDensityClusteringAggregation:
    def test_metric_and_threshold(self) -> None:
        aggregator = create_aggregator(delta=2.0)
        alerts = [make_alert("a", 1.0), make_alert("b", 4.0)]

        assert aggregator.metric(alerts) == [[0.0, 3.0], [3.0, 0.0]]
        assert aggregator.metric(alerts, return_last_rows=1) == [[3.0, 0.0]]
        assert aggregator._check_threshold([[0.0, 2.0], [2.1, 0.0]]) == [
            [True, True],
            [False, True],
        ]

    def test_aggregate_assigns_and_merges_groups(self) -> None:
        aggregator = create_aggregator(delta=1.0)
        first = make_alert("a", 0.0)
        second = make_alert("b", 10.0)
        bridge = make_alert("c", 5.0)

        first_output = AggregateSchema()
        assert aggregator.aggregate_alerts(first, first_output)
        assert first_output["alertDetails"]["a"] == "0"

        second_output = AggregateSchema()
        aggregator.aggregate_alerts(second, second_output)
        assert second_output["alertDetails"]["b"] == "1"

        bridge_output = AggregateSchema()
        aggregator.config.delta = 6.0
        aggregator.aggregate_alerts(bridge, bridge_output)

        assert bridge_output["alertDetails"]["c"] == "0"
        assert aggregator.active_groups == {0: {0, 1}, 1: {0, 1}}
        assert "Groups" in bridge_output["alertDetails"]["messages"]

    def test_duplicate_alert_is_not_reassigned(self) -> None:
        aggregator = create_aggregator()
        alert = make_alert("same", 0.0)

        first_output = AggregateSchema()
        aggregator.aggregate_alerts(alert, first_output)
        duplicate_output = AggregateSchema()
        aggregator.aggregate_alerts(alert, duplicate_output)

        assert "same" not in duplicate_output["alertDetails"]
        assert aggregator.next_group_id == 1
        assert len(aggregator.relevant_alerts) == 1

    def test_window_buffer_keeps_latest_alerts(self) -> None:
        aggregator = create_aggregator(
            buffer_mode=BufferMode.WINDOW,
            buffer_size=2,
        )
        alerts = [
            make_alert("discard-1", 0.0),
            make_alert("keep-1", 0.0),
            make_alert("keep-2", 0.0),
        ]
        aggregator.relevant_alerts.extend(alerts)
        aggregator.alert_id_to_group_id.update(
            {alert["alertID"]: 0 for alert in alerts}
        )

        discarded, affected_groups = aggregator._discard_alerts()

        assert discarded == ["discard-1"]
        assert affected_groups == {0}
        assert [alert["alertID"] for alert in aggregator.relevant_alerts] == [
            "keep-1",
            "keep-2",
        ]

    def test_default_hooks_raise_not_implemented(self) -> None:
        aggregator = DensityClusteringAggregation(
            config=DensityClusteringAggregationConfig(delta=1.0)
        )
        alert = make_alert("a", 0.0)

        with pytest.raises(NotImplementedError):
            aggregator.single_metric(alert, alert)
        with pytest.raises(NotImplementedError):
            aggregator.discard_alert_fn([alert])
