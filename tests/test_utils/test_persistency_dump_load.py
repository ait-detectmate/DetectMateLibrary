import pytest
from dataclasses import dataclass

from detectmatelibrary.utils.persistency.exceptions import PersistencyLoadError
from detectmatelibrary.utils.persistency.event_data_structures.base import EventDataStructure
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)


def test_persistency_load_error_is_exception():
    err = PersistencyLoadError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_event_data_structure_has_dump_load():
    assert hasattr(EventDataStructure, "dump")
    assert hasattr(EventDataStructure, "load")


def test_subclass_without_dump_load_cannot_be_instantiated():
    @dataclass
    class _Incomplete(EventDataStructure):
        def add_data(self, data_object): pass
        def get_data(self): pass
        def get_variables(self): pass
        def to_data(self, raw_data): pass
        # intentionally missing dump() and load()

    with pytest.raises(TypeError):
        _Incomplete()


class TestSingleStabilityTrackerState:
    def _make_tracker(self) -> SingleStabilityTracker:
        t = SingleStabilityTracker(min_samples=3)
        for v in ["a", "b", "a", "c", "a"]:
            t.add_value(v)
        return t

    def test_round_trip_preserves_change_series(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert list(t2.change_series) == list(t.change_series)

    def test_round_trip_preserves_unique_set(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert t2.unique_set == t.unique_set

    def test_round_trip_preserves_min_samples(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert t2.min_samples == 3

    def test_round_trip_preserves_classification(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert t2.classify().type == t.classify().type

    def test_state_includes_type_and_module(self):
        t = SingleStabilityTracker()
        state = t.to_state()
        assert state["type"] == "SingleStabilityTracker"
        assert "module" in state

    def test_empty_tracker_round_trip(self):
        t = SingleStabilityTracker(min_samples=5)
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert len(t2.change_series) == 0
        assert len(t2.unique_set) == 0
