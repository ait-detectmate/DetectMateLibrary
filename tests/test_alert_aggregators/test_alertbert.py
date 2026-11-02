from pathlib import Path

import numpy as np
import pytest

from detectmatelibrary.alert_aggregation.alertbert import (
    AlertBERTAggregation,
    AlertBERTAggregationConfig,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema


def make_alerts(count: int) -> list[DetectorSchema]:
    random = np.random.default_rng(42)
    descriptions = random.choice(np.array(["a", "b", "c", "d"]), size=count)
    severities = random.choice(np.array(["w", "e"]), size=count)
    return [
        DetectorSchema(
            {
                "detectorID": "detector",
                "detectorType": "alertbert-test",
                "alertID": f"alert-{i}",
                "detectedTimestamp": i,
                "logIDs": [f"log-{i}"],
                "score": 0.0,
                "logTimestamps": [i],
                "description": str(descriptions[i]),
                "receivedTimestamp": i,
                "alertDetails": {"severity": str(severities[i])},
            }
        )
        for i in range(count)
    ]


def make_config(path: Path, train_model: bool) -> AlertBERTAggregationConfig:
    return AlertBERTAggregationConfig(
        path=str(path),
        model_id="alertbert-integration",
        train_model=train_model,
        delta=1.0,
        theta=1.0,
        clustering_backend="scipy",
        train_size=50_000,
        val_size=10_000,
        min_freq=1,
        features=("description", "alertDetails:severity"),
        n_heads=1,
        dim_per_head=4,
        num_layers=1,
        context_size=1024,
        batch_size=1,
        updates=(49, 49),
        warm_up_steps=1,
    )


def test_alertbert_aggregation_training_saving_loading_and_inference(
    tmp_path: Path,
) -> None:
    alerts = make_alerts(100_000)
    training_alerts = alerts[:60_000]
    first_inference = alerts[60_000:80_000]
    second_inference = alerts[80_000:]

    aggregator = AlertBERTAggregation(make_config(tmp_path, train_model=True))
    training_output = AggregateSchema()
    assert aggregator.aggregate_alerts(training_alerts, training_output)
    assert aggregator.config.train_model is False
    assert training_output["alertDetails"]

    model_path = tmp_path / "alertbert-integration"
    assert (model_path / "model.pt").exists()
    assert (model_path / "report.json").exists()
    assert (model_path / "vocab_description.json").exists()
    assert (model_path / "vocab_alertDetails:severity.json").exists()

    first_output = AggregateSchema()
    assert aggregator.aggregate_alerts(first_inference, first_output)
    assert len(first_output["alertDetails"]) >= len(first_inference)
    assert {
        alert["alertID"] for alert in first_inference
    }.issubset(first_output["alertDetails"])

    loaded_aggregator = AlertBERTAggregation(make_config(tmp_path, train_model=False))
    second_output = AggregateSchema()
    assert loaded_aggregator.aggregate_alerts(second_inference, second_output)
    assert len(second_output["alertDetails"]) >= len(second_inference)
    assert {
        alert["alertID"] for alert in second_inference
    }.issubset(second_output["alertDetails"])
    assert second_output["description"] == "Alert aggregation by the AlertBERT method."
    assert set(loaded_aggregator.mlm.config["features"]) == {
        "description",
        "alertDetails:severity",
    }

    loaded_aggregator.config.clustering_backend = "detectmate"
    detectmate_output = AggregateSchema()
    assert loaded_aggregator.aggregate_alerts(second_inference[:10], detectmate_output)
    assert {
        alert["alertID"] for alert in second_inference[:10]
    }.issubset(detectmate_output["alertDetails"])


def test_alertbert_config_excludes_aggregation_fields(tmp_path: Path) -> None:
    config = make_config(tmp_path, train_model=True)

    model_config = config._get_mlm_config()

    assert model_config["features"] == ("description", "alertDetails:severity")
    assert "buffer_size" not in model_config
    assert "clustering_backend" not in model_config
    assert "delta" not in model_config
    assert "layers" not in model_config


def test_alertbert_training_requires_explicit_datasets(
    tmp_path: Path,
) -> None:
    aggregator = AlertBERTAggregation(make_config(tmp_path, train_model=True))

    with pytest.raises(ValueError, match="train_data and val_data"):
        aggregator._train_mlm(use_gathered_alerts=False)


def test_alertbert_discards_alerts_outside_delta(tmp_path: Path) -> None:
    aggregator = AlertBERTAggregation(make_config(tmp_path, train_model=True))
    alerts = make_alerts(3)
    alerts[1]["logTimestamps"] = [0]
    alerts[2]["logTimestamps"] = [2]
    aggregator.relevant_alerts = alerts
    aggregator.config.delta = 1.0

    assert aggregator.discard_alert_fn(alerts) == [True, True, False]
