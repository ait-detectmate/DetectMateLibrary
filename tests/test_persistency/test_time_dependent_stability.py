"""Tests for the segmentation option of the stability trackers."""

import logging
import math

import detectmatelibrary.schemas as schemas
from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.common.variable_detector import VariableAutoConfigParams
from detectmatelibrary.utils.persistency.rle_list import RLEList
from detectmatelibrary.utils.persistency import EventPersistency
from detectmatelibrary.utils.persistency.event_data_structures.trackers import (
    StabilityClassifier,
    SingleStabilityTracker,
    EventStabilityTracker,
)

THRESHOLDS = [1.1, 0.3, 0.1, 0.01]  # same defaults SingleStabilityTracker uses


def make_classifier() -> StabilityClassifier:
    return StabilityClassifier(segment_thresholds=THRESHOLDS)


# Divergence fixture: 3 changes up front, then a quiet tail of 37.
# In *time*, the changes span most of the observed window and the quiet
# tail is a burst compressed into ~0.04s at the end.
#
# The three change stamps are spaced so that each equal-duration quarter of the
# window holds exactly one occurrence (boundaries [0, 1, 2, 3, 40]), which is
# what puts a lone mean of 1.0 into a quarter whose threshold is 0.3.
DIVERGENT_SERIES = [True, True, True] + [False] * 37
DIVERGENT_TIMES = [0.0, 30.0, 60.0] + [90.0 + 0.001 * i for i in range(37)]

# Burst fixture: 20 fresh values, each immediately repeated once, inside 40 ms,
# then a single further repeat an hour later. Equal-duration quarters put all 40
# early occurrences in quarter 0 and leave quarters 1 and 2 with nothing in them,
# which scores them 0.0 -- so time mode calls this churning variable STABLE and
# only count mode (or `both`) catches it.
BURSTY_VALUES = [f"v{i // 2}" for i in range(40)] + ["v19"]
BURSTY_SERIES = [True, False] * 20 + [False]
BURSTY_TIMES = [0.001 * i for i in range(40)] + [3600.0]

# Opposite-direction divergence fixture. DIVERGENT_* above is count-STABLE and
# time-UNSTABLE; this one is count-UNSTABLE and time-STABLE. 30 fresh values one
# second apart, then the same value repeated 10 times spread over ~17 minutes.
#
#   count quarters -> means [1.0, 1.0, 1.0, 0.0]   -> UNSTABLE (segments 2 and 3)
#   time quarters  -> means [0.938, 0.0, 0.0, 0.0] -> STABLE (0.938 < 1.1)
#
# The pair of fixtures is what makes "both" testable in each direction: neither
# segmentation subsumes the other.
CHURN_VALUES = [f"v{i}" for i in range(30)] + ["v29"] * 10
CHURN_TIMES = [float(i) for i in range(30)] + [100.0 * (i + 1) for i in range(10)]

# Both segmentations agree on STABLE: two values, then one of them repeated,
# evenly spaced so the duration cuts coincide with the count cuts.
# Both give means [0.2, 0.0, 0.0, 0.0].
AGREE_VALUES = ["a", "b"] + ["b"] * 38
AGREE_TIMES = [float(i) for i in range(40)]


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

    def test_empty_time_segment_scores_zero(self):
        """An empty segment means nothing was observed in that window, so its
        mean is 0.0 -- the boundaries are kept, not discarded.

        Equal-duration cuts of BURSTY_TIMES give boundaries [0, 40, 40,
        40, 41] and means [0.5, 0.0, 0.0, 0.0], which passes: time mode
        alone is lenient on a burst followed by silence. Count mode
        still sees the churn, so `both` catches it.
        """
        clf_count = make_classifier()
        assert clf_count.is_stable(RLEList(BURSTY_SERIES)) is False

        clf_time = make_classifier()
        assert clf_time.is_stable(RLEList(BURSTY_SERIES), timestamps=BURSTY_TIMES) is True
        assert clf_time.get_last_segment_means() == [0.5, 0.0, 0.0, 0.0]

    def test_empty_time_segment_scores_zero_on_plain_list_path(self):
        clf_time = make_classifier()
        assert clf_time.is_stable(list(BURSTY_SERIES), timestamps=BURSTY_TIMES) is True
        assert clf_time.get_last_segment_means() == [0.5, 0.0, 0.0, 0.0]

    def test_out_of_order_timestamps_fall_back_to_count_mode(self):
        """np.searchsorted requires sorted input.

        UNSORTED_TIMES is SORTED_TIMES with two entries transposed --
        what a multi-source merge or concurrent writers produce.
        Unguarded, the cuts land at [0, 9, 20, 31, 40] instead of [0,
        10, 20, 30, 40], turning the exact means [0.5, 0.5, 0.5, 0.5]
        into [0.556, 0.455, 0.545, 0.444] -- wrong, and silently so.
        """
        series = [True, False] * 20
        sorted_times = [float(i) for i in range(40)]
        unsorted_times = list(sorted_times)
        unsorted_times[9], unsorted_times[30] = unsorted_times[30], unsorted_times[9]

        clf_count = make_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_classifier()
        assert clf_time.is_stable(RLEList(series), timestamps=unsorted_times) == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_sorted_timestamps_still_use_time_mode(self):
        """The monotonicity guard must not disable time mode for valid
        input."""
        clf = make_classifier()
        assert clf.is_stable(RLEList(DIVERGENT_SERIES), timestamps=DIVERGENT_TIMES) is False
        count = make_classifier()
        count.is_stable(RLEList(DIVERGENT_SERIES))
        assert clf.get_last_segment_means() != count.get_last_segment_means()

    def test_equal_timestamps_are_not_treated_as_out_of_order(self):
        """Duplicate stamps are non-decreasing, so they stay in time mode."""
        series = [True, False] * 20
        times = [float(i // 2) for i in range(40)]  # each stamp used twice
        clf = make_classifier()
        assert clf.is_stable(RLEList(series), timestamps=times) is False
        assert not any(math.isnan(mean) for mean in clf.get_last_segment_means())

    def test_list_and_rle_agree_on_ragged_length(self):
        """13 items over 4 segments: both paths must cut identically."""
        series = [True, False, True] + [False] * 10
        clf_list = make_classifier()
        clf_list.is_stable(list(series))
        clf_rle = make_classifier()
        clf_rle.is_stable(RLEList(series))
        assert clf_list.get_last_segment_means() == clf_rle.get_last_segment_means()


def feed_divergent(tracker: SingleStabilityTracker) -> None:
    """3 new values spread over ~80s, then a repeated value bursting at
    t~100."""
    values = ["a", "b", "c"] + ["c"] * 37
    for value, ts in zip(values, DIVERGENT_TIMES):
        tracker.add_value(value, timestamp=ts)


def feed_churn(tracker: SingleStabilityTracker) -> None:
    """30 new values one second apart, then a repeated value over ~17 min."""
    for value, ts in zip(CHURN_VALUES, CHURN_TIMES):
        tracker.add_value(value, timestamp=ts)


def feed_agreeing(tracker: SingleStabilityTracker) -> None:
    """One change up front, then a settled value, evenly spaced."""
    for value, ts in zip(AGREE_VALUES, AGREE_TIMES):
        tracker.add_value(value, timestamp=ts)


class TestSingleStabilityTrackerSegmentation:
    def test_timestamps_stored_only_when_enabled(self):
        on = SingleStabilityTracker(segmentation="time")
        on.add_value("a", timestamp=1.0)
        on.add_value("b", timestamp=2.0)
        assert on.timestamps == [1.0, 2.0]

        off = SingleStabilityTracker()  # default segmentation="count"
        off.add_value("a", timestamp=1.0)
        assert off.timestamps == []

    def test_classification_diverges_between_modes(self):
        count_mode = SingleStabilityTracker()
        feed_divergent(count_mode)
        assert count_mode.classify().type == "STABLE"

        time_mode = SingleStabilityTracker(segmentation="time")
        feed_divergent(time_mode)
        assert time_mode.classify().type == "UNSTABLE"

    def test_missing_timestamps_fall_back_to_count_mode(self):
        # time segmentation on, but values arrive without timestamps
        tracker = SingleStabilityTracker(segmentation="time")
        for value in ["a", "b", "c"] + ["c"] * 37:
            tracker.add_value(value)
        reference = SingleStabilityTracker()
        for value in ["a", "b", "c"] + ["c"] * 37:
            reference.add_value(value)
        assert tracker.classify().type == reference.classify().type

    def test_round_trip_preserves_time_state(self):
        tracker = SingleStabilityTracker(segmentation="time")
        feed_divergent(tracker)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.segmentation == "time"
        assert restored.timestamps == tracker.timestamps
        assert restored.classify().type == "UNSTABLE"

    def test_legacy_state_without_time_keys_defaults_off(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        state.pop("segmentation", None)  # simulate pre-flag snapshot
        state.pop("timestamps", None)
        restored = SingleStabilityTracker.from_state(state)
        assert restored.segmentation == "count"
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

    def test_bursty_series_needs_the_count_pass(self):
        """A burst followed by silence is time-STABLE (empty quarters score
        0.0) but count-UNSTABLE, so only `both` refuses to hand it to auto-
        config variable selection as a monitoring candidate."""
        trackers = {
            mode: SingleStabilityTracker(segmentation=mode)
            for mode in ("count", "time", "both")
        }
        for value, ts in zip(BURSTY_VALUES, BURSTY_TIMES):
            for tracker in trackers.values():
                tracker.add_value(value, timestamp=ts)
        assert trackers["count"].classify().type == "UNSTABLE"
        assert trackers["time"].classify().type == "STABLE"
        assert trackers["both"].classify().type == "UNSTABLE"


class TestSegmentationPlumbing:
    def test_event_tracker_propagates_flag_and_timestamp(self):
        event_tracker = EventStabilityTracker(segmentation="time")
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        single = event_tracker.get_data()["var1"]
        assert single.segmentation == "time"
        assert single.timestamps == [1.0, 2.0]

    def test_ingest_event_forwards_timestamp(self):
        storage = EventPersistency(
            EventStabilityTracker,
            event_data_kwargs={"segmentation": "time"},
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
        event_tracker = EventStabilityTracker(segmentation="time")
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        restored = EventStabilityTracker.load(event_tracker.dump(), segmentation="time")
        single = restored.get_data()["var1"]
        assert single.segmentation == "time"
        assert single.timestamps == [1.0, 2.0]


class TestSegmentationWithDetectorAddValueFn:
    """Segmentation="time" must work when a detector owns the value
    semantics."""

    def test_detector_backed_tracker_records_timestamps(self):
        tracker = SingleStabilityTracker(
            add_value_fn="CharsetDetector", segmentation="time"
        )
        tracker.add_value("ab", timestamp=1.0)
        tracker.add_value("cd", timestamp=2.0)
        assert tracker.unique_set == {"a", "b", "c", "d"}
        assert tracker.timestamps == [1.0, 2.0]
        assert len(tracker.timestamps) == len(tracker.change_series)

    def test_value_range_skipped_value_keeps_alignment(self):
        """ValueRangeDetector returns early on non-numeric input without
        appending to change_series; timestamps must not drift."""
        tracker = SingleStabilityTracker(
            add_value_fn="ValueRangeDetector", segmentation="time"
        )
        tracker.add_value("1", timestamp=1.0)
        tracker.add_value("not-a-number", timestamp=2.0)  # detector records nothing
        tracker.add_value("5", timestamp=3.0)
        assert len(tracker.change_series) == 2
        assert tracker.timestamps == [1.0, 3.0]

    def test_event_tracker_detector_backed_round_trip(self):
        event_tracker = EventStabilityTracker(
            add_value_fn="CharsetDetector", segmentation="time"
        )
        event_tracker.add_data({"var1": "ab"}, timestamp=1.0)
        event_tracker.add_data({"var1": "cd"}, timestamp=2.0)
        restored = EventStabilityTracker.load(
            event_tracker.dump(), add_value_fn="CharsetDetector", segmentation="time"
        )
        single = restored.get_data()["var1"]
        assert single.unique_set == {"a", "b", "c", "d"}
        assert single.timestamps == [1.0, 2.0]


def _parser_record(ts_value, event_id=1):
    return schemas.ParserSchema({
        "parserType": "test",
        "EventID": event_id,
        "template": "test template",
        "variables": ["abc"],
        "logID": "1",
        "parsedLogID": "1",
        "parserID": "test_parser",
        "log": "test log message",
        "logFormatVariables": {"ts": ts_value},
    })


class TestTimestampResolution:
    # Each test below constructs CharsetDetector(config=CharsetDetectorConfig())
    # explicitly rather than bare CharsetDetector(). CharsetDetector.__init__'s
    # `config` default argument is a single shared CharsetDetectorConfig()
    # instance (pre-existing mutable-default-arg pitfall, see
    # TestSegmentationConfigWiring.test_flag_reaches_per_variable_trackers), and
    # several tests here mutate `detector.config.*` in place -- writing through
    # to that shared instance and leaking state into any other bare-constructed
    # CharsetDetector for the rest of the process. Passing a fresh config keeps
    # every test isolated regardless of run order.
    def test_returns_none_when_not_configured(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) is None

    def test_parses_iso_timestamp(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.segmentation = "time"
        detector.config.auto_config_params.timestamp_variable = "ts"
        assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) == 1785837600.0

    def test_parses_explicit_format(self):
        """HDFS loghub style, absent from COMMON_TIME_FORMATS."""
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.segmentation = "time"
        detector.config.auto_config_params.timestamp_variable = "ts"
        detector.config.auto_config_params.timestamp_format = "%y%m%d %H%M%S"
        first = detector._timestamp(_parser_record("081109 203615"))
        second = detector._timestamp(_parser_record("081109 203645"))
        assert second - first == 30.0

    def test_unparseable_warns_once_and_falls_back(self, caplog):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.segmentation = "time"
        detector.config.auto_config_params.timestamp_variable = "ts"
        with caplog.at_level(logging.WARNING):
            assert detector._timestamp(_parser_record("not-a-time")) is None
            assert detector._timestamp(_parser_record("also-not-a-time")) is None
        warnings = [r for r in caplog.records if "timestamp_variable" in r.message]
        assert len(warnings) == 1

    def test_unset_timestamp_variable_warns_once_and_falls_back(self, caplog):
        """Segmentation="time" without timestamp_variable is an operator error,
        not an opt-out: it must be distinguishable from a working time-
        dependent run, and must not flood the log."""
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.segmentation = "time"  # timestamp_variable left unset
        with caplog.at_level(logging.WARNING):
            assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) is None
            assert detector._timestamp(_parser_record("2026-08-04 10:00:01")) is None
        warnings = [r for r in caplog.records if "timestamp_variable" in r.message]
        assert len(warnings) == 1
        assert "not set" in warnings[0].message

    def test_flag_off_stays_silent(self, caplog):
        """No warning when the feature simply is not enabled."""
        detector = CharsetDetector(config=CharsetDetectorConfig())
        with caplog.at_level(logging.WARNING):
            assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) is None
        assert not [r for r in caplog.records if "timestamp_variable" in r.message]

    def test_missing_variable_warns_and_falls_back(self, caplog):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.segmentation = "time"
        detector.config.auto_config_params.timestamp_variable = "absent"
        with caplog.at_level(logging.WARNING):
            assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) is None
        assert any("timestamp_variable" in r.message for r in caplog.records)


class TestSegmentationConfigWiring:
    def test_flag_reaches_per_variable_trackers(self):
        # CharsetDetector's `config` parameter default is a single shared
        # CharsetDetectorConfig() instance (pre-existing mutable-default-arg
        # pitfall, unrelated to segmentation). Other tests in this
        # module mutate `detector.config.*` in place on a bare
        # CharsetDetector(), so we pass explicit fresh configs here to stay
        # isolated from that.
        # segmentation only shapes the configure-phase persistency: the
        # trained persistency is read by _check_variable, which never calls
        # classify(), so it never receives stability kwargs at all.
        detector = CharsetDetector(config=CharsetDetectorConfig())
        assert detector.persistency.event_data_kwargs.get("segmentation") is None

        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.auto_config_params.segmentation = "time"
        rebuilt = CharsetDetector(config=configured.config.to_dict(method_id="CharsetDetector"))
        assert rebuilt.auto_conf_persistency.event_data_kwargs["segmentation"] == "time"

    def test_config_fields_round_trip(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.segmentation = "time"
        detector.config.auto_config_params.timestamp_variable = "ts"
        detector.config.auto_config_params.timestamp_format = "%y%m%d %H%M%S"
        restored = type(detector.config).from_dict(
            detector.config.to_dict(method_id="CharsetDetector"), "CharsetDetector"
        )
        assert restored.auto_config_params.segmentation == "time"
        assert restored.auto_config_params.timestamp_variable == "ts"
        assert restored.auto_config_params.timestamp_format == "%y%m%d %H%M%S"

    def test_configure_populates_timestamps_end_to_end(self):
        """Segmentation settings reach the configure-phase persistency's
        trackers end-to-end.

        This used to run through train()/.persistency, but the trained
        path no longer receives stability kwargs at all (see
        test_train_path_records_no_timestamps) -- configure()/
        .auto_conf_persistency is the phase these settings are for.
        """
        cfg = CharsetDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                segmentation="time",
                timestamp_variable="ts",
                timestamp_format="%y%m%d %H%M%S",
            ),
        )
        detector = CharsetDetector(config=cfg, name="CharsetDetector")
        detector.configure(_parser_record("081109 203615"))
        detector.configure(_parser_record("081109 203645"))
        tracker = detector.auto_conf_persistency.get_events_data()[1].get_data()["var_0"]
        assert tracker.segmentation == "time"
        assert len(tracker.timestamps) == len(tracker.change_series) == 2
        assert tracker.timestamps[1] - tracker.timestamps[0] == 30.0

    def test_segmentation_fields_survive_auto_config_set_configuration(self):
        """set_configuration() writes only self.config.events and then flips
        auto_config to False -- it never rebuilds or reassigns self.config
        wholesale, so auto_config_params (like every other operator-set field,
        e.g. `persist`) is left untouched by construction.

        auto_config defaults to True and core.py runs
        set_configuration() before train(), so this is the path every
        detector takes unless auto_config is explicitly disabled.
        """
        cfg = CharsetDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                segmentation="time",
                timestamp_variable="ts",
                timestamp_format="%y%m%d %H%M%S",
            ),
        )
        detector = CharsetDetector(config=cfg, name="CharsetDetector")
        assert detector.config.auto_config is True

        for _ in range(5):
            detector.configure(_parser_record("081109 203615"))
        detector.set_configuration()

        assert detector.config.auto_config_params.segmentation == "time"
        assert detector.config.auto_config_params.timestamp_variable == "ts"
        assert detector.config.auto_config_params.timestamp_format == "%y%m%d %H%M%S"


class TestBothSegmentation:
    """`both` is STABLE only when count and time segmentation agree."""

    def test_rejects_when_only_time_is_unstable(self):
        count_mode = SingleStabilityTracker()
        feed_divergent(count_mode)
        assert count_mode.classify().type == "STABLE"

        time_mode = SingleStabilityTracker(segmentation="time")
        feed_divergent(time_mode)
        assert time_mode.classify().type == "UNSTABLE"

        both_mode = SingleStabilityTracker(segmentation="both")
        feed_divergent(both_mode)
        assert both_mode.classify().type == "UNSTABLE"

    def test_rejects_when_only_count_is_unstable(self):
        """The opposite direction: proves neither pass is dead code."""
        count_mode = SingleStabilityTracker()
        feed_churn(count_mode)
        assert count_mode.classify().type == "UNSTABLE"

        time_mode = SingleStabilityTracker(segmentation="time")
        feed_churn(time_mode)
        assert time_mode.classify().type == "STABLE"

        both_mode = SingleStabilityTracker(segmentation="both")
        feed_churn(both_mode)
        assert both_mode.classify().type == "UNSTABLE"

    def test_accepts_when_both_agree(self):
        """`both` must not be vacuously strict."""
        for mode in ("count", "time", "both"):
            tracker = SingleStabilityTracker(segmentation=mode)
            feed_agreeing(tracker)
            assert tracker.classify().type == "STABLE", mode

    def test_without_timestamps_matches_count_mode(self):
        """No usable timestamps -> the time pass runs on count boundaries, so
        `both` degrades to plain `count` rather than to a free pass.

        Uses CHURN_VALUES (count-UNSTABLE) precisely because an
        implementation that degrades to an unconditional free pass would
        also call an all-STABLE fixture STABLE here; only a fixture that
        is UNSTABLE when fed without timestamps can tell the two apart.
        """
        both_mode = SingleStabilityTracker(segmentation="both")
        reference = SingleStabilityTracker()
        for value in CHURN_VALUES:
            both_mode.add_value(value)  # no timestamp argument
            reference.add_value(value)
        assert reference.classify().type == "UNSTABLE"
        assert both_mode.classify().type == "UNSTABLE"

    def test_reason_reports_both_mean_vectors(self):
        """The note must carry the *actual* count and time mean vectors, not
        just the words "count"/"time" -- and they must be distinct, which
        catches a snapshot-ordering bug where the time pass's overwrite of
        StabilityClassifier.segment_means leaks into the count half of the note
        (see the comment at the count_means snapshot in _is_stable()).

        feed_churn is used because its count and time means genuinely
        differ ([1.0, 1.0, 1.0, 0.0] vs [0.9375, 0.0, 0.0, 0.0]); it
        also yields UNSTABLE, so this exercises the note on the branch
        finding 1 wires it into.
        """
        tracker = SingleStabilityTracker(segmentation="both")
        feed_churn(tracker)
        classification = tracker.classify()
        assert classification.type == "UNSTABLE"
        reason = classification.reason
        assert "count [1.0, 1.0, 1.0, 0.0]" in reason
        assert "time [0.9375, 0.0, 0.0, 0.0]" in reason

    def test_round_trip_preserves_both_mode(self):
        tracker = SingleStabilityTracker(segmentation="both")
        feed_churn(tracker)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.segmentation == "both"
        assert restored.timestamps == tracker.timestamps
        assert restored.classify().type == "UNSTABLE"

    def test_stability_note_is_not_persisted(self):
        tracker = SingleStabilityTracker(segmentation="both")
        feed_agreeing(tracker)
        tracker.classify()
        assert "_stability_note" not in tracker.to_state()

    def test_config_accepts_both_and_reaches_trackers(self):
        # segmentation only shapes the configure-phase persistency (see
        # TestSegmentationConfigWiring.test_flag_reaches_per_variable_trackers).
        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.auto_config_params.segmentation = "both"
        rebuilt = CharsetDetector(
            config=configured.config.to_dict(method_id="CharsetDetector")
        )
        assert rebuilt.auto_conf_persistency.event_data_kwargs["segmentation"] == "both"

    def test_event_tracker_propagates_both(self):
        event_tracker = EventStabilityTracker(segmentation="both")
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        single = event_tracker.get_data()["var1"]
        assert single.segmentation == "both"
        assert single.timestamps == [1.0, 2.0]


def test_train_path_records_no_timestamps():
    """Auto-config settings shape the configure-phase persistency only.

    Stability classification is never consulted at detect time, so the
    trained trackers would carry an unread timestamps list per variable.
    """
    from detectmatelibrary.common.variable_detector import VariableAutoConfigParams
    from detectmatelibrary.detectors.new_value_detector import (
        NewValueDetector,
        NewValueDetectorConfig,
    )

    detector = NewValueDetector(
        name="NewValueDetector",
        config=NewValueDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                segmentation="time", timestamp_variable="ts",
            ),
        ),
    )
    records = [_parser_record(f"2026-08-04 10:{i:02d}:00") for i in range(20)]
    for record in records:
        detector.configure(record)
    detector.set_configuration()
    for record in records:
        detector.train(record)

    trained = detector.persistency.get_events_data()[1].get_data()
    assert trained, "expected the configure phase to select at least one variable"
    for tracker in trained.values():
        assert tracker.segmentation == "count"
        assert tracker.timestamps == []

    # the configure-phase persistency still gets them
    configured = detector.auto_conf_persistency.get_events_data()[1].get_data()
    assert any(t.segmentation == "time" for t in configured.values())


def test_persisted_state_omits_auto_config_params():
    """Persisted tracker state never carries auto_config_params: they are
    configure-phase-only inputs, and CharsetDetector's add_value closure
    (recovered from `detector_config` on reconstruction, see
    _strip_auto_config_params in variable_detector.py) reads only
    operational fields, never auto_config_params.
    """
    cfg = CharsetDetectorConfig(
        auto_config_params=VariableAutoConfigParams(
            segmentation="time", timestamp_variable="ts",
        ),
    )
    detector = CharsetDetector(config=cfg, name="CharsetDetector")
    for _ in range(5):
        detector.configure(_parser_record("2026-08-04 10:00:00"))
    detector.set_configuration()
    detector.train(_parser_record("2026-08-04 10:00:00"))

    trained = detector.persistency.get_events_data()[1].get_data()
    assert trained, "expected the configure phase to select at least one variable"
    for tracker in trained.values():
        state = tracker.to_state()
        entry = state["detector_config"]["detectors"]["CharsetDetector"]
        assert "auto_config_params" not in entry
