"""Tests for the time-axis classification methods on the stability trackers."""
from detectmatelibrary.utils.persistency import EventPersistency
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    SingleStabilityTracker,
    EventStabilityTracker,
    ClassificationMethods,
)
from tests.support.stability import BURSTY_TIMES, BURSTY_VALUES, feed_divergent


class TestSingleStabilityTrackerSegmentation:
    def test_timestamps_stored_only_when_enabled(self):
        on = SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True))
        on.add_value("a", timestamp=1.0)
        on.add_value("b", timestamp=2.0)
        assert on.timestamps == [1.0, 2.0]

        off = SingleStabilityTracker()  # default classification=ClassificationMethods(index=True)
        off.add_value("a", timestamp=1.0)
        assert off.timestamps == []

    def test_classification_diverges_between_modes(self):
        count_mode = SingleStabilityTracker()
        feed_divergent(count_mode)
        assert count_mode.classify().type == "STABLE"

        time_mode = SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True))
        feed_divergent(time_mode)
        assert time_mode.classify().type == "UNSTABLE"

    def test_missing_timestamps_fall_back_to_index_mode(self):
        # time classification on, but values arrive without timestamps
        tracker = SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True))
        for value in ["a", "b", "c"] + ["c"] * 37:
            tracker.add_value(value)
        reference = SingleStabilityTracker()
        for value in ["a", "b", "c"] + ["c"] * 37:
            reference.add_value(value)
        assert tracker.classify().type == reference.classify().type

    def test_round_trip_preserves_time_state(self):
        tracker = SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True))
        feed_divergent(tracker)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.classification == ClassificationMethods(index=False, time=True)
        assert restored.timestamps == tracker.timestamps
        assert restored.classify().type == "UNSTABLE"

    def test_legacy_state_without_time_keys_defaults_off(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        state.pop("classification", None)  # simulate pre-flag snapshot
        state.pop("timestamps", None)
        restored = SingleStabilityTracker.from_state(state)
        assert restored.classification == ClassificationMethods(index=True)
        assert restored.timestamps == []

    def test_legacy_state_without_add_value_keys_loads(self):
        """A snapshot old enough to predate add_value_fn/detector_config must
        still load; those keys were indexed, not .get()-ed, so it raised
        KeyError."""
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        state.pop("add_value_fn", None)
        state.pop("detector_config", None)
        state["expand_value"] = True  # the flag such a snapshot would carry
        restored = SingleStabilityTracker.from_state(state)
        assert restored.add_value_fn == "default"
        assert restored.detector_config is None
        assert restored.unique_set == {"hello"}

    def test_bursty_series_needs_the_index_pass(self):
        """A burst followed by silence is time-STABLE (empty quarters score
        0.0) but index-UNSTABLE, so only `both` refuses to hand it to auto-
        config variable selection as a monitoring candidate."""
        trackers = {
            "index": SingleStabilityTracker(classification=ClassificationMethods(index=True)),
            "time": SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True)),
            "both": SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True)),
        }
        for value, ts in zip(BURSTY_VALUES, BURSTY_TIMES):
            for tracker in trackers.values():
                tracker.add_value(value, timestamp=ts)
        assert trackers["index"].classify().type == "UNSTABLE"
        assert trackers["time"].classify().type == "STABLE"
        assert trackers["both"].classify().type == "UNSTABLE"


class TestSegmentationPlumbing:
    def test_event_tracker_propagates_flag_and_timestamp(self):
        event_tracker = EventStabilityTracker(
            classification=ClassificationMethods(index=False, time=True)
        )
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        single = event_tracker.get_data()["var1"]
        assert single.classification == ClassificationMethods(index=False, time=True)
        assert single.timestamps == [1.0, 2.0]

    def test_ingest_event_forwards_timestamp(self):
        storage = EventPersistency(
            event_data_kwargs={"classification": {"index": False, "time": True}},
        )
        storage.ingest_event(1, "tpl <*>", variables=["a"], timestamp=10.0)
        storage.ingest_event(1, "tpl <*>", variables=["b"], timestamp=20.0)
        single = storage.get_events_data()[1].get_data()["var_0"]
        assert single.timestamps == [10.0, 20.0]

    def test_ingest_event_without_timestamp_still_works(self):
        storage = EventPersistency()
        storage.ingest_event(1, "tpl <*>", variables=["a"])
        single = storage.get_events_data()[1].get_data()["var_0"]
        assert list(single.change_series) == [True]
        assert single.timestamps == []

    def test_event_tracker_dump_load_preserves_timestamps(self):
        event_tracker = EventStabilityTracker(
            classification=ClassificationMethods(index=False, time=True)
        )
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        restored = EventStabilityTracker.load(
            event_tracker.dump(), classification={"index": False, "time": True}
        )
        single = restored.get_data()["var1"]
        assert single.classification == ClassificationMethods(index=False, time=True)
        assert single.timestamps == [1.0, 2.0]
