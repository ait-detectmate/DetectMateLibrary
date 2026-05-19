from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
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


class TestEventStabilityTrackerExpandValue:
    def test_default_event_tracker_uses_add_semantics(self):
        event_tracker = EventStabilityTracker()
        event_tracker.add_data({"var1": "hello"})
        single = event_tracker.get_data()["var1"]
        assert single.expand_value is False
        assert single.unique_set == {"hello"}

    def test_expand_value_propagates_to_per_variable_trackers(self):
        event_tracker = EventStabilityTracker(expand_value=True)
        event_tracker.add_data({"var1": "hello"})
        event_tracker.add_data({"var1": "world"})
        single = event_tracker.get_data()["var1"]
        assert single.expand_value is True
        assert single.unique_set == {"h", "e", "l", "o", "w", "r", "d"}

    def test_each_new_variable_gets_its_own_configured_tracker(self):
        event_tracker = EventStabilityTracker(expand_value=True)
        event_tracker.add_data({"a": "ab", "b": "cd"})
        a = event_tracker.get_data()["a"]
        b = event_tracker.get_data()["b"]
        assert a.expand_value is True
        assert b.expand_value is True
        assert a.unique_set == {"a", "b"}
        assert b.unique_set == {"c", "d"}

    def test_post_load_new_variable_honors_expand_value(self):
        """After dump/load, a variable that wasn't present at save time should
        still use expand_value semantics when first ingested."""
        original = EventStabilityTracker(expand_value=True)
        original.add_data({"known": "abc"})
        blob = original.dump()
        restored = EventStabilityTracker.load(blob, expand_value=True)

        # Ingest a brand-new variable not present in the saved state
        restored.add_data({"known": "de", "newvar": "xy"})

        new_tracker = restored.get_data()["newvar"]
        assert new_tracker.expand_value is True
        assert new_tracker.unique_set == {"x", "y"}

        # And the existing variable continues to expand correctly
        known_tracker = restored.get_data()["known"]
        assert known_tracker.expand_value is True
        assert {"a", "b", "c", "d", "e"} <= known_tracker.unique_set
