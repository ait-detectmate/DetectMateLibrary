"""Contract every detector honours: ParserSchema in, DetectorSchema alerts
out, after an optional training phase.

Each check runs for every detector in tests/contract/registry.py. A case's
`normal` and `anomalous` probes come after its `train` records; DeepLog and
LogBERT have no probes (their alerts depend on a trained model, see
unit/detectors/), so they only get the interface checks.
"""
import pytest
from pydantic import ValidationError

import detectmatelibrary.schemas as sc
from detectmatelibrary import detectors
from detectmatelibrary.base_detectors import TrackerDetector
from detectmatelibrary.schemas._classes import FieldNotFound, set_connector
from tests.contract.registry import DETECTORS, cases, raw_log

WITH_NORMAL = [case for case in DETECTORS if case.normal is not None]
WITH_ANOMALOUS = [case for case in DETECTORS if case.anomalous is not None]


def _alerts(detector, records: list) -> list:
    return [out for out in map(detector.process, records) if out is not None]


def test_every_exported_detector_is_registered():
    exported = {name for name in detectors.__all__ if not name.endswith("Config")}
    assert exported - {case.cls.__name__ for case in DETECTORS} == set()


@pytest.mark.parametrize("case", cases(DETECTORS))
def test_tracker_flag_matches_the_class(case):
    """The tracker checks run for exactly the TrackerDetector subclasses."""
    assert case.tracker == issubclass(case.cls, TrackerDetector)


@pytest.mark.parametrize("case", cases(WITH_NORMAL))
def test_normal_input_raises_no_alert(case):
    assert _alerts(case.trained(), case.normal()) == []


@pytest.mark.parametrize("case", cases(WITH_ANOMALOUS))
class TestAlerts:
    def test_anomalous_input_raises_an_alert(self, case):
        detector = case.trained()
        records = case.anomalous()
        alerts = _alerts(detector, records)

        assert alerts
        known_ids = {record["logID"] for record in case.train() + records}
        for alert in alerts:
            assert isinstance(alert, sc.DetectorSchema)
            assert alert["detectorID"] == case.name
            assert alert["detectorType"] == detector.config.method_type
            assert alert["alertID"]
            assert alert["score"] > 0
            assert len(alert["logIDs"]) == case.window
            assert set(alert["logIDs"]) <= known_ids
            assert alert["logIDs"][-1] in {record["logID"] for record in records}  # ends at the trigger
        assert len({alert["alertID"] for alert in alerts}) == len(alerts)

    def test_bytes_in_bytes_out(self, case):
        alerts = _alerts(case.trained(), [record.serialize() for record in case.anomalous()])

        assert alerts and all(isinstance(alert, bytes) for alert in alerts)
        decoded = sc.DetectorSchema()
        decoded.deserialize(alerts[0])
        assert decoded["detectorID"] == case.name

    def test_input_is_not_modified(self, case):
        records = case.anomalous()
        before = [record.copy() for record in records]
        _alerts(case.trained(), records)
        assert records == before

    def test_output_is_stored_through_the_connector(self, case):
        set_connector("Verification")
        for alert in _alerts(case.trained(), case.anomalous()):
            assert sc.DetectorSchema.from_id(alert["alertID"]) == alert

    def test_alerts_name_the_parser_they_listen_to(self, case):
        alerts = _alerts(case.trained(parser="parser"), case.anomalous())
        assert {alert["detectorID"] for alert in alerts} == {f"{case.name}_from_parser"}

    def test_records_of_other_parsers_are_ignored(self, case):
        detector = case.trained(parser="parser")
        records = case.anomalous()
        for record in records:
            record["parserID"] = "another_parser"
        assert _alerts(detector, records) == []


@pytest.mark.parametrize("case", cases([case for case in DETECTORS if case.window > 1]))
def test_no_output_until_the_window_is_full(case):
    detector = case.build()
    records = case.train()[:case.window - 1]
    assert [detector.process(record) for record in records] == [None] * (case.window - 1)


@pytest.mark.parametrize("case", cases(DETECTORS))
def test_raw_logs_are_rejected(case):
    detector = case.build()
    with pytest.raises(FieldNotFound):
        for i in range(case.window):
            detector.process(raw_log(i))


@pytest.mark.parametrize("case", cases([case for case in DETECTORS if case.train()], trains=True))
def test_training_phase_ends_after_data_use_training(case):
    train = case.train()
    detector = case.build(data_use_training=len(train) - case.window + 1)
    for record in train:
        detector.process(record)
    assert detector.get_state() == "Training"

    detector.process(train[-1])
    assert detector.get_state() == "Default"


@pytest.mark.parametrize("case", cases([case for case in DETECTORS if not case.tracker]))
def test_persist_is_rejected_on_non_trackers(case):
    config = case.yaml()
    config["detectors"][case.name]["persist"] = {"path": "memory://contract/state"}
    with pytest.raises(ValidationError, match="persist"):
        case.cls(name=case.name, config=config)
