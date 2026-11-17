"""Tests for detectmatelibrary._testutils.dummy_alert_aggregator: the sliding
window of three alerts that other tests rely on (its interface is checked by
tests/contract)."""
import detectmatelibrary.schemas as sc
from detectmatelibrary._testutils.dummy_alert_aggregator import DummyAlertAggregator


def _alert(i: int) -> sc.DetectorSchema:
    return sc.DetectorSchema({"detectorID": "detector", "alertID": f"a{i}", "logIDs": [str(i)]})


def test_aggregates_a_sliding_window_of_three_alerts():
    aggregator = DummyAlertAggregator()
    outputs = [aggregator.process(_alert(i)) for i in range(4)]

    assert [output is not None for output in outputs] == [False, False, True, True]
    assert set(outputs[2]["alertIDs"]) == {"a0", "a1", "a2"}
    assert set(outputs[3]["alertIDs"]) == {"a1", "a2", "a3"}
    assert outputs[3]["description"] == "Dummy alert aggregation"
