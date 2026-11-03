# --8<-- [start:example_1]
import numpy as np
import yaml

from detectmatelibrary.alert_aggregation.alertbert import (
    AlertBERTAggregation,
)
from detectmatelibrary.schemas import DetectorSchema
from detectmatelibrary.tools.logging import logger

with open("docs/examples/alert_aggregators/alertbert.yaml") as f:
    config = yaml.safe_load(f)


def alert_generator(count: int) -> iter[DetectorSchema]:
    random = np.random.default_rng(42)
    descriptions = random.choice(
        np.array(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]),
        p=[0.2, 0.15, 0.15, 0.1, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05],
        size=count,
    )  # nosec B311
    severities = random.choice(
        np.array(["w", "e", "c"]),
        p=[0.5, 0.3, 0.2],
        size=count,
    )  # nosec B311
    hostnames = random.choice(
        np.array(["host1", "host2", "host3", "host4", "host5", "host6"]),
        p=[0.2, 0.2, 0.2, 0.15, 0.15, 0.1],
        size=count,
    )  # nosec B311
    timestamps = np.floor(
        np.cumulative_sum(random.exponential(scale=1.2, size=count))
    ).astype(int)
    yield from [
        DetectorSchema(
            {
                "detectorID": "detector",
                "detectorType": "alertbert-test",
                "alertID": f"alert-{i}",
                "detectedTimestamp": timestamps[i],
                "logIDs": [f"log-{i}"],
                "score": 0.0,
                "logTimestamps": [timestamps[i]],
                "description": str(descriptions[i]),
                "receivedTimestamp": timestamps[i],
                "alertDetails": {
                    "severity": str(severities[i]),
                    "hostname": str(hostnames[i]),
                },
            }
        )
        for i in range(count)
    ]


aggregator = AlertBERTAggregation(config)
outputs = []

for alert in alert_generator(80_000):
    output = aggregator.process(alert)
    if output is not None:
        outputs.append(output)

logger.info("Processed all alerts!")

# --8<-- [end:example_1]
