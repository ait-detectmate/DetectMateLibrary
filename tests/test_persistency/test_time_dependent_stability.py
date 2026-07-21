"""Tests for the time_dependent option of the stability trackers."""

from detectmatelibrary.utils.persistency.rle_list import RLEList
from detectmatelibrary.utils.persistency import EventPersistency
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability import (
    EventStabilityTracker,
    SingleStabilityTracker,
    StabilityClassifier,
)

THRESHOLDS = [1.1, 0.3, 0.1, 0.01]  # same defaults SingleStabilityTracker uses


def make_classifier() -> StabilityClassifier:
    return StabilityClassifier(segment_thresholds=THRESHOLDS)


# Divergence fixture: 3 changes up front, then a quiet tail of 37.
# In *time*, the changes span most of the observed window and the quiet
# tail is a burst compressed into ~0.04s at the end.
DIVERGENT_SERIES = [True, True, True] + [False] * 37
DIVERGENT_TIMES = [0.0, 40.0, 80.0] + [100.0 + 0.001 * i for i in range(37)]


class TestClassifierTimeBoundaries:
    def test_count_mode_is_stable_on_divergent_fixture(self):
        clf = make_classifier()
        # count segments of 10: means [0.3, 0, 0, 0] -> all below thresholds
        assert clf.is_stable(RLEList(DIVERGENT_SERIES)) is True

    def test_time_mode_is_unstable_on_divergent_fixture(self):
        clf = make_classifier()
        # time quarters put a lone change (mean 1.0) into segment 2 (thresh 0.3)
        assert clf.is_stable(RLEList(DIVERGENT_SERIES), timestamps=DIVERGENT_TIMES) is False

    def test_uniform_timestamps_match_count_mode(self):
        # N divisible by n_segments -> boundaries coincide exactly
        series = [True, False, False, True, False, False, False, False]
        ts = [float(i) for i in range(8)]
        clf_count = make_classifier()
        clf_count.is_stable(RLEList(series))
        clf_time = make_classifier()
        clf_time.is_stable(RLEList(series), timestamps=ts)
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_plain_list_path_supports_timestamps(self):
        clf = make_classifier()
        assert clf.is_stable(list(DIVERGENT_SERIES), timestamps=DIVERGENT_TIMES) is False

    def test_zero_span_falls_back_to_count_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_classifier()
        result = clf_time.is_stable(RLEList(series), timestamps=[5.0] * 8)
        assert result == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_length_mismatch_falls_back_to_count_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_classifier()
        assert clf_time.is_stable(RLEList(series), timestamps=[1.0, 2.0]) == expected

    def test_none_timestamp_entry_falls_back_to_count_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_classifier()
        ts = [0.0, 1.0, None, 3.0, 4.0, 5.0, 6.0, 7.0]
        assert clf_time.is_stable(RLEList(series), timestamps=ts) == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_nan_timestamp_entry_falls_back_to_count_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_classifier()
        ts = [0.0, 1.0, float("nan"), 3.0, 4.0, 5.0, 6.0, 7.0]
        assert clf_time.is_stable(RLEList(series), timestamps=ts) == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()


def feed_divergent(tracker: SingleStabilityTracker) -> None:
    """3 new values spread over ~80s, then a repeated value bursting at
    t~100."""
    values = ["a", "b", "c"] + ["c"] * 37
    for value, ts in zip(values, DIVERGENT_TIMES):
        tracker.add_value(value, timestamp=ts)


class TestSingleStabilityTrackerTimeDependent:
    def test_timestamps_stored_only_when_enabled(self):
        on = SingleStabilityTracker(time_dependent=True)
        on.add_value("a", timestamp=1.0)
        on.add_value("b", timestamp=2.0)
        assert on.timestamps == [1.0, 2.0]

        off = SingleStabilityTracker()  # default time_dependent=False
        off.add_value("a", timestamp=1.0)
        assert off.timestamps == []

    def test_classification_diverges_between_modes(self):
        count_mode = SingleStabilityTracker()
        feed_divergent(count_mode)
        assert count_mode.classify().type == "STABLE"

        time_mode = SingleStabilityTracker(time_dependent=True)
        feed_divergent(time_mode)
        assert time_mode.classify().type == "UNSTABLE"

    def test_missing_timestamps_fall_back_to_count_mode(self):
        # time_dependent on, but values arrive without timestamps
        tracker = SingleStabilityTracker(time_dependent=True)
        for value in ["a", "b", "c"] + ["c"] * 37:
            tracker.add_value(value)
        reference = SingleStabilityTracker()
        for value in ["a", "b", "c"] + ["c"] * 37:
            reference.add_value(value)
        assert tracker.classify().type == reference.classify().type

    def test_round_trip_preserves_time_state(self):
        tracker = SingleStabilityTracker(time_dependent=True)
        feed_divergent(tracker)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.time_dependent is True
        assert restored.timestamps == tracker.timestamps
        assert restored.classify().type == "UNSTABLE"

    def test_legacy_state_without_time_keys_defaults_off(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        state.pop("time_dependent", None)  # simulate pre-flag snapshot
        state.pop("timestamps", None)
        restored = SingleStabilityTracker.from_state(state)
        assert restored.time_dependent is False
        assert restored.timestamps == []


class TestTimeDependentPlumbing:
    def test_event_tracker_propagates_flag_and_timestamp(self):
        event_tracker = EventStabilityTracker(time_dependent=True)
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        single = event_tracker.get_data()["var1"]
        assert single.time_dependent is True
        assert single.timestamps == [1.0, 2.0]

    def test_ingest_event_forwards_timestamp(self):
        storage = EventPersistency(
            EventStabilityTracker,
            event_data_kwargs={"time_dependent": True},
        )
        storage.ingest_event(1, "tpl <*>", variables=["a"], timestamp=10.0)
        storage.ingest_event(1, "tpl <*>", variables=["b"], timestamp=20.0)
        single = storage.get_events_data()[1].get_data()["var_0"]
        assert single.timestamps == [10.0, 20.0]

    def test_ingest_event_without_timestamp_still_works(self):
        storage = EventPersistency(EventStabilityTracker)
        storage.ingest_event(1, "tpl <*>", variables=["a"])
        single = storage.get_events_data()[1].get_data()["var_0"]
        assert list(single.change_series) == [True]
        assert single.timestamps == []

    def test_event_tracker_dump_load_preserves_timestamps(self):
        event_tracker = EventStabilityTracker(time_dependent=True)
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        restored = EventStabilityTracker.load(event_tracker.dump(), time_dependent=True)
        single = restored.get_data()["var1"]
        assert single.time_dependent is True
        assert single.timestamps == [1.0, 2.0]
