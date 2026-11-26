"""Contract every tracker detector honours: its state can be saved,
restored and federated.

The parametrized checks run for every TRACKER_DETECTORS case in
tests/contract/registry.py: after a restore or a federation, a detector must
report exactly what a detector trained on the same data reports.
"""
from pathlib import Path

import fsspec
import pytest

from detectmatelibrary.utils.persistency import PersistencyLoadError
from tests.contract.registry import TRACKER_DETECTORS, cases

FEDERATED = [case for case in TRACKER_DETECTORS if case.binary]


def _probes(case) -> list:
    return [*case.normal(), *case.anomalous()]


def _detections(detector, case) -> list:
    """What `detector` reports for each probe, without IDs and timestamps.

    The first window - 1 probes are left out: they only fill the window,
    and a restored detector starts with an empty one.
    """
    outputs = [detector.process(record) for record in _probes(case)][case.window - 1:]
    return [None if out is None else (list(out["logIDs"]), out["score"]) for out in outputs]


def _expected(case) -> list:
    detections = _detections(case.trained(), case)
    assert any(detections), "the probes must raise at least one alert"
    return detections


@pytest.mark.parametrize("case", cases(TRACKER_DETECTORS))
class TestPersist:
    def test_no_saver_without_persist(self, case):
        assert case.build().saver is None

    def test_persist_saves_the_store_on_exit(self, case):
        with case.build(persist={"path": "memory://contract/state"}) as detector:
            assert detector.saver is not None
            assert detector.saver._persistency is detector.persistency

        assert fsspec.filesystem("memory").exists(f"contract/state/{case.name}/metadata.json")

    def test_auto_load_restores_the_state(self, case):
        with case.trained(persist={"path": "memory://contract/state"}):
            pass  # saves on exit

        with case.build(persist={"path": "memory://contract/state", "auto_load": True}) as restored:
            assert _detections(restored, case) == _expected(case)


@pytest.mark.parametrize("case", cases(TRACKER_DETECTORS))
class TestExportImport:
    @pytest.mark.parametrize("target", [None, "memory://contract/export"], ids=["bytes", "path"])
    def test_imported_state_gives_the_same_detections(self, case, target):
        trained = case.trained()
        exported = trained.export_state(target)
        if target is None:
            assert isinstance(exported, bytes)
            state = exported
        else:
            assert exported is None, "export_state(path) writes to the path and returns nothing"
            state = target

        restored = case.build()
        restored.import_state(state)

        assert _detections(restored, case) == _expected(case)

    def test_export_leaves_the_saver_cadence_alone(self, case):
        """export_state() is a snapshot, not a save: it must not reset the
        counter that times the background saver."""
        detector = case.trained()
        before = detector.persistency._events_since_save
        assert before > 0

        detector.export_state("memory://contract/export")

        assert detector.persistency._events_since_save == before

    def test_missing_state_raises_and_keeps_the_learned_state(self, case):
        detector = case.trained()

        with pytest.raises(PersistencyLoadError):
            detector.import_state("memory://contract/never_saved")

        assert _detections(detector, case) == _expected(case)


@pytest.mark.parametrize("case", cases(FEDERATED))
class TestFederation:
    def test_binary_round_trip_gives_the_same_detections(self, case):
        trained = case.trained(allow_fed=True)
        copy = trained.from_binary(trained.to_binary())
        copy.update_state("stop_training")  # the copy starts its config's training phase again (Q-F)

        assert _detections(copy, case) == _expected(case)

    @pytest.mark.parametrize("join", ["add", "stack", "stack_binary"])
    def test_federated_detectors_know_what_each_learned(self, case, join):
        """Two detectors trained on the two halves of the training data report
        what one detector trained on all of it reports.

        The detector that saw the end of the training data receives the
        other's state: its sliding window then matches the reference.
        """
        first, last = _halves(case)

        if join == "add":
            (last + first).aggregate()
        else:
            last.stack(first if join == "stack" else first.to_binary())
            last.aggregate()

        assert _detections(last, case) == _expected(case)

    def test_aggregate_returns_the_federated_state(self, case):
        first, last = _halves(case)
        last.stack(first)

        copy = case.build(allow_fed=True).from_binary(last.aggregate())
        copy.update_state("stop_training")

        assert _detections(copy, case) == _expected(case)

    def test_finalize_federation_removes_the_slow_table(self, case):
        detector = case.trained(allow_fed=True)
        assert Path(".temp").exists()

        detector.finalize_federation()

        assert not Path(".temp").exists()


def _trained_on(case, records: list):
    detector = case.build(allow_fed=True, data_use_training=len(records) - case.window + 1)
    for record in records:
        detector.process(record)
    return detector


def _halves(case) -> tuple:
    """Two detectors trained on the two halves of the training data.

    The federation checks only have teeth if neither half is enough on its
    own: a detector trained on one half must report something else than
    the reference, or a merge that drops the other half would still pass.
    """
    train = case.train()
    half = len(train) // 2
    for part in (train[:half], train[half:]):
        assert _detections(_trained_on(case, part), case) != _expected(case), (
            "one half of the training data already gives the reference detections; "
            "give each half something the probes need"
        )
    return _trained_on(case, train[:half]), _trained_on(case, train[half:])


@pytest.mark.parametrize("case", cases(TRACKER_DETECTORS))
def test_finalize_federation_without_allow_fed_changes_nothing(case):
    detector = case.trained()
    detector.finalize_federation()
    assert _detections(detector, case) == _expected(case)
