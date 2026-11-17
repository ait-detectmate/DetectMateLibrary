"""Tests for detectmatelibrary.detectors.random_detector."""
import numpy as np
import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary.detectors.random_detector import RandomDetector

pytestmark = pytest.mark.usefixtures("frozen_timestamps")


def _detector(threshold: float) -> RandomDetector:
    return RandomDetector(name="TestDetector", config={"detectors": {"TestDetector": {
        "method_type": "random_detector",
        "auto_config": False,
        "events": {1: {"test": {"variables": [
            {"pos": 0, "name": "process", "params": {"threshold": threshold}},
        ]}}},
    }}})


def _record(event_id: int = 1) -> sc.ParserSchema:
    return sc.ParserSchema({"eventID": event_id, "variables": ["var1"], "logID": "1", "headerVariables": {}})


def test_alerts_when_the_draw_exceeds_the_threshold():
    """Each configured variable draws np.random.rand() and alerts above its
    threshold; with seed 0 the draws are .549 .715 .603 .545 .424 .646."""
    detector = _detector(threshold=0.5)
    np.random.seed(0)
    assert [detector.detect(_record(), sc.DetectorSchema()) for _ in range(6)] == [True] * 4 + [False, True]


def test_threshold_zero_always_alerts_and_names_the_variable():
    alert = sc.DetectorSchema()
    assert _detector(threshold=0.0).detect(_record(), alert) is True
    assert alert["score"] == 1.0
    assert dict(alert["alertDetails"]) == {"process": "1.0"}


def test_threshold_one_never_alerts():
    detector = _detector(threshold=1.0)
    assert not any(detector.detect(_record(), sc.DetectorSchema()) for _ in range(50))


def test_unconfigured_event_never_alerts():
    assert _detector(threshold=0.0).detect(_record(event_id=2), sc.DetectorSchema()) is False
