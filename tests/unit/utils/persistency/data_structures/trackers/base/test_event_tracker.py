"""Tests for detectmatelibrary.utils.persistency.data_structures.trackers.base.

event_tracker.
"""
from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
)


class TestEventTrackerDumpLoad:
    def _make_tracker(self) -> EventStabilityTracker:
        t = EventStabilityTracker()
        for i in range(10):
            t.add_data({"var_0": f"value_{i % 3}", "var_1": str(i)})
        return t

    def test_dump_returns_bytes(self):
        t = self._make_tracker()
        assert isinstance(t.dump(), bytes)

    def test_round_trip_restores_tracker_keys(self):
        t = self._make_tracker()
        t2 = EventStabilityTracker.load(t.dump())
        assert set(t2.get_data().keys()) == set(t.get_data().keys())

    def test_round_trip_preserves_change_series(self):
        t = self._make_tracker()
        t2 = EventStabilityTracker.load(t.dump())
        for key in t.get_data():
            original = list(t.get_data()[key].change_series)
            restored = list(t2.get_data()[key].change_series)
            assert restored == original

    def test_round_trip_preserves_unique_set(self):
        t = self._make_tracker()
        t2 = EventStabilityTracker.load(t.dump())
        for key in t.get_data():
            assert t2.get_data()[key].unique_set == t.get_data()[key].unique_set

    def test_empty_tracker_round_trip(self):
        t = EventStabilityTracker()
        t2 = EventStabilityTracker.load(t.dump())
        assert t2.get_data() == {}
