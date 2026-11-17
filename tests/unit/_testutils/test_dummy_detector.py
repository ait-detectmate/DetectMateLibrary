"""Tests for detectmatelibrary._testutils.dummy_detector: the alternating
alerts that pipeline and buffering tests rely on (its interface is checked by
tests/contract)."""
import detectmatelibrary.schemas as sc
from detectmatelibrary._testutils.dummy_detector import DummyDetector


def _record(i: int) -> sc.ParserSchema:
    return sc.ParserSchema({"logID": str(i), "log": "test log", "headerVariables": {"Time": "0"}})


def test_alerts_on_every_second_record():
    detector = DummyDetector()
    outputs = [detector.process(_record(i)) for i in range(4)]
    assert [output is not None for output in outputs] == [False, True, False, True]


def test_alert_content():
    detector = DummyDetector()
    detector.process(_record(0))
    alert = detector.process(_record(1))

    assert alert["description"] == "Dummy detection process"
    assert alert["score"] == 1.0
    assert alert["alertDetails"]["type"] == "Anomaly detected by DummyDetector"
