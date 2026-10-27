# --8<-- [start:example_1]
import yaml

from detectmatelibrary.alert_aggregation.density_clustering import (
    DensityClusteringAggregation,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema

with open("docs/examples/alert_aggregators/density_cluster.yaml") as f:
    config = yaml.safe_load(f)


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
    def single_metric(
        self,
        alert1: DetectorSchema,
        alert2: DetectorSchema
    ) -> float:
        return abs(alert1["score"] - alert2["score"])

    def discard_alert_fn(self, alerts: list[DetectorSchema]) -> list[bool]:
        return [False for alert in alerts]


aggregator = ConcreteDensityClusteringAggregation(config)
first = make_alert("a", 0.0)
second = make_alert("b", 6.0)
bridge = make_alert("c", 3.0)

first_output = AggregateSchema()
aggregator.aggregate_alerts(first, first_output)

second_output = AggregateSchema()
aggregator.aggregate_alerts(second, second_output)

bridge_output = AggregateSchema()
aggregator.aggregate_alerts(bridge, bridge_output)

print(first_output["alertDetails"]["a"] == "0")  # True
print(second_output["alertDetails"]["b"] == "1")  # True
print(bridge_output["alertDetails"]["c"] == "0")  # True

# group labels 0 and 1 are merged into a single group
print(aggregator.active_groups[1] == {0, 1})  # True

# --8<-- [end:example_1]
