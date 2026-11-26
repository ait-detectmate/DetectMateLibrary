"""Tests for detectmatelibrary.utils.alertbert.datasets."""
import numpy as np
import pytest
import torch
from detectmatelibrary.schemas import DetectorSchema
from detectmatelibrary.utils.alertbert.datasets import (
    AlertDataset,
    AlertSequenceBatchSampler,
    AlertSequenceSampler,
    MergeAlertSequences,
    detectorschema_to_dict,
    split_alert_dataset,
)


def make_alert(
    alert_id: str, timestamp: int, description: str = "login"
) -> DetectorSchema:
    return DetectorSchema(
        {
            "detectorID": "detector",
            "detectorType": "dummy",
            "alertID": alert_id,
            "detectedTimestamp": timestamp,
            "logIDs": [f"log-{alert_id}"],
            "score": 0.0,
            "logTimestamps": [timestamp],
            "description": description,
            "receivedTimestamp": timestamp,
            "alertDetails": {"severity": "low"},
        }
    )


def test_alert_dataset_converts_alerts_and_supports_indexing() -> None:
    alerts = [make_alert(str(i), i, description=f"event-{i}") for i in range(3)]
    dataset = AlertDataset(alerts)

    assert len(dataset) == 3
    assert dataset[0]["relevantTimestamp"] == 0
    assert dataset[-1]["alertID"] == "2"
    assert dataset[1:]["alertID"] == ["1", "2"]
    assert dataset[np.array([2, 0])]["alertID"] == ["2", "0"]
    assert detectorschema_to_dict(alerts[0])["alertDetails:severity"] == "low"
    with pytest.raises(TypeError):
        dataset["invalid"]  # type: ignore[index]


def test_split_dataset_and_sequence_samplers() -> None:
    dataset = AlertDataset(make_alert(str(i), i) for i in range(10))
    train, validation, test = split_alert_dataset(
        dataset, (0.5, 0.3, 0.2), drop_first_n=2
    )

    assert len(train) == 4
    assert len(validation) == 2
    assert len(test) == 2
    assert train[0]["alertID"] == "2"
    with pytest.raises(ValueError):
        split_alert_dataset(dataset, (0.5, 0.5, 0.5))

    generator = torch.Generator().manual_seed(2)
    sampler = AlertSequenceSampler(
        dataset, context_size=3, cyclic=False, generator=generator, shuffle=False
    )
    slices = list(sampler)
    assert len(sampler) == 3
    assert all(s.stop - s.start == 3 for s in slices)
    batches = list(
        AlertSequenceBatchSampler(
            dataset, context_size=3, batch_size=2, drop_last=False
        )
    )
    assert len(batches) == 2
    cyclic = AlertSequenceSampler(
        dataset, context_size=4, cyclic=True, generator=generator, shuffle=False
    )
    assert len(list(cyclic)) == 3


def test_merge_alert_sequences_orders_sources_and_skips_empty_sources() -> None:
    sources = {
        "first": iter([make_alert("a", 1), make_alert("c", 3)]),
        "second": iter([make_alert("b", 2)]),
    }
    merged = MergeAlertSequences(sources)
    merged.add_source("empty", iter([]))

    assert [alert["alertID"] for alert in merged] == ["a", "b", "c"]
    merged.add_source("later", iter([make_alert("d", 4)]))
    assert [alert["alertID"] for alert in merged] == ["d"]
