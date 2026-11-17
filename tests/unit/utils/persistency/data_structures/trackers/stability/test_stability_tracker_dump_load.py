
from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    ClassificationMethods,
)


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

    def test_non_default_thresholds_round_trip_inside_the_block(self):
        tracker = SingleStabilityTracker(
            min_samples=3,
            classification=ClassificationMethods(segment_thresholds=[0.5, 0.25, 0.125]),
        )
        for v in ["a", "b", "a", "c", "a"]:
            tracker.add_value(v)
        state = tracker.to_state()
        assert "segment_thresholds" not in state
        restored = SingleStabilityTracker.from_state(state)
        assert restored.stability_classifier.segment_threshs == [0.5, 0.25, 0.125]
        assert restored.classification == tracker.classification
        assert restored.to_state()["classification"] == state["classification"]
