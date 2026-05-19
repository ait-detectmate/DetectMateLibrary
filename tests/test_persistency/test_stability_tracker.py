from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)


class TestSingleStabilityTrackerExpandValue:
    def test_default_add_stores_whole_value(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        tracker.add_value("world")
        assert tracker.unique_set == {"hello", "world"}

    def test_expand_value_unions_characters(self):
        tracker = SingleStabilityTracker(expand_value=True)
        tracker.add_value("hello")
        tracker.add_value("world")
        assert tracker.unique_set == {"h", "e", "l", "o", "w", "r", "d"}

    def test_expand_value_change_series_tracks_growth(self):
        tracker = SingleStabilityTracker(expand_value=True)
        tracker.add_value("ab")           # adds {a, b}, change=True
        tracker.add_value("ba")           # adds nothing new, change=False
        tracker.add_value("c")            # adds {c}, change=True
        assert list(tracker.change_series) == [True, False, True]

    def test_expand_value_round_trip(self):
        tracker = SingleStabilityTracker(expand_value=True)
        tracker.add_value("hello")
        tracker.add_value("world")
        state = tracker.to_state()
        restored = SingleStabilityTracker.from_state(state)
        assert restored.expand_value is True
        assert restored.unique_set == {"h", "e", "l", "o", "w", "r", "d"}
        # subsequent ingestion still unions characters
        restored.add_value("xy")
        assert {"x", "y"} <= restored.unique_set

    def test_legacy_state_without_expand_value_defaults_false(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        state.pop("expand_value", None)  # simulate pre-flag snapshot
        restored = SingleStabilityTracker.from_state(state)
        assert restored.expand_value is False
        assert restored.unique_set == {"hello"}
