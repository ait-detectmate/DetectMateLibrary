"""Tests for the time_dependent option of the stability trackers."""

import logging

import detectmatelibrary.schemas as schemas
from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
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
# window holds at least one occurrence (boundaries [0, 1, 2, 3, 40]). An empty
# quarter would trip the empty-segment fallback in _segment_boundaries and drop
# the fixture back to count mode -- see
# TestClassifierTimeBoundaries.test_empty_time_segment_falls_back_to_count_mode.
DIVERGENT_SERIES = [True, True, True] + [False] * 37
DIVERGENT_TIMES = [0.0, 30.0, 60.0] + [90.0 + 0.001 * i for i in range(37)]

# Burst fixture: 20 fresh values, each immediately repeated once, inside 40 ms,
# then a single further repeat an hour later. Equal-duration quarters put all 40
# early occurrences in quarter 0 and leave quarters 1 and 2 with nothing in them.
BURSTY_VALUES = [f"v{i // 2}" for i in range(40)] + ["v19"]
BURSTY_SERIES = [True, False] * 20 + [False]
BURSTY_TIMES = [0.001 * i for i in range(40)] + [3600.0]


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

    def test_empty_time_segment_falls_back_to_count_mode(self):
        """A segment with no occurrences has a nan mean, and `not nan >=
        thresh` is True -- an unconditional pass.

        Raw equal-duration cuts of BURSTY_TIMES give boundaries [0, 40,
        40, 40, 41] and means [0.5, nan, nan, 0.0]: two free passes plus
        segment 0 (whose 1.1 threshold is unreachable by a mean of
        booleans), which is enough to call this churning variable
        stable. Equal-count cuts keep every segment populated, so time
        mode must defer to them here.
        """
        clf_count = make_classifier()
        expected = clf_count.is_stable(RLEList(BURSTY_SERIES))
        assert expected is False  # count mode sees the churn

        clf_time = make_classifier()
        assert clf_time.is_stable(RLEList(BURSTY_SERIES), timestamps=BURSTY_TIMES) is False
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_empty_time_segment_fallback_on_plain_list_path(self):
        clf_count = make_classifier()
        expected = clf_count.is_stable(list(BURSTY_SERIES))
        clf_time = make_classifier()
        assert clf_time.is_stable(list(BURSTY_SERIES), timestamps=BURSTY_TIMES) == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

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
        assert not any(mean != mean for mean in clf.get_last_segment_means())  # no nan

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

    def test_bursty_series_is_unstable_in_both_modes(self):
        """Time mode must not turn a churning variable STABLE.

        Empty equal-duration segments would pass unconditionally (means
        [0.5, nan, nan, 0.0]) and hand this variable to auto-config
        variable selection as a monitoring candidate.
        """
        count_mode = SingleStabilityTracker()
        time_mode = SingleStabilityTracker(time_dependent=True)
        for value, ts in zip(BURSTY_VALUES, BURSTY_TIMES):
            count_mode.add_value(value)
            time_mode.add_value(value, timestamp=ts)
        assert count_mode.classify().type == "UNSTABLE"
        assert time_mode.classify().type == "UNSTABLE"


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


class TestTimeDependentWithDetectorAddValueFn:
    """time_dependent must work when a detector owns the value semantics."""

    def test_detector_backed_tracker_records_timestamps(self):
        tracker = SingleStabilityTracker(
            add_value_fn="CharsetDetector", time_dependent=True
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
            add_value_fn="ValueRangeDetector", time_dependent=True
        )
        tracker.add_value("1", timestamp=1.0)
        tracker.add_value("not-a-number", timestamp=2.0)  # detector records nothing
        tracker.add_value("5", timestamp=3.0)
        assert len(tracker.change_series) == 2
        assert tracker.timestamps == [1.0, 3.0]

    def test_event_tracker_detector_backed_round_trip(self):
        event_tracker = EventStabilityTracker(
            add_value_fn="CharsetDetector", time_dependent=True
        )
        event_tracker.add_data({"var1": "ab"}, timestamp=1.0)
        event_tracker.add_data({"var1": "cd"}, timestamp=2.0)
        restored = EventStabilityTracker.load(
            event_tracker.dump(), add_value_fn="CharsetDetector", time_dependent=True
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
    # TestTimeDependentConfigWiring.test_flag_reaches_per_variable_trackers), and
    # several tests here mutate `detector.config.*` in place -- writing through
    # to that shared instance and leaking state into any other bare-constructed
    # CharsetDetector for the rest of the process. Passing a fresh config keeps
    # every test isolated regardless of run order.
    def test_returns_none_when_not_configured(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) is None

    def test_parses_iso_timestamp(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.time_dependent = True
        detector.config.timestamp_variable = "ts"
        assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) == 1785837600.0

    def test_parses_explicit_format(self):
        """HDFS loghub style, absent from COMMON_TIME_FORMATS."""
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.time_dependent = True
        detector.config.timestamp_variable = "ts"
        detector.config.timestamp_format = "%y%m%d %H%M%S"
        first = detector._timestamp(_parser_record("081109 203615"))
        second = detector._timestamp(_parser_record("081109 203645"))
        assert second - first == 30.0

    def test_unparseable_warns_once_and_falls_back(self, caplog):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.time_dependent = True
        detector.config.timestamp_variable = "ts"
        with caplog.at_level(logging.WARNING):
            assert detector._timestamp(_parser_record("not-a-time")) is None
            assert detector._timestamp(_parser_record("also-not-a-time")) is None
        warnings = [r for r in caplog.records if "timestamp_variable" in r.message]
        assert len(warnings) == 1

    def test_unset_timestamp_variable_warns_once_and_falls_back(self, caplog):
        """time_dependent without timestamp_variable is an operator error, not
        an opt-out: it must be distinguishable from a working time-dependent
        run, and must not flood the log."""
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.time_dependent = True  # timestamp_variable left unset
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
        detector.config.time_dependent = True
        detector.config.timestamp_variable = "absent"
        with caplog.at_level(logging.WARNING):
            assert detector._timestamp(_parser_record("2026-08-04 10:00:00")) is None
        assert any("timestamp_variable" in r.message for r in caplog.records)


class TestTimeDependentConfigWiring:
    def test_flag_reaches_per_variable_trackers(self):
        # CharsetDetector's `config` parameter default is a single shared
        # CharsetDetectorConfig() instance (pre-existing mutable-default-arg
        # pitfall, unrelated to time_dependent). Other tests in this module
        # mutate `detector.config.*` in place on a bare CharsetDetector(), so
        # we pass explicit fresh configs here to stay isolated from that.
        detector = CharsetDetector(config=CharsetDetectorConfig())
        assert detector.persistency.event_data_kwargs.get("time_dependent") is None

        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.time_dependent = True
        rebuilt = CharsetDetector(config=configured.config.to_dict(method_id="CharsetDetector"))
        assert rebuilt.persistency.event_data_kwargs["time_dependent"] is True

    def test_config_fields_round_trip(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.time_dependent = True
        detector.config.timestamp_variable = "ts"
        detector.config.timestamp_format = "%y%m%d %H%M%S"
        restored = type(detector.config).from_dict(
            detector.config.to_dict(method_id="CharsetDetector"), "CharsetDetector"
        )
        assert restored.time_dependent is True
        assert restored.timestamp_variable == "ts"
        assert restored.timestamp_format == "%y%m%d %H%M%S"

    def test_train_populates_timestamps_end_to_end(self):
        cfg = {
            "detectors": {
                "CharsetDetector": {
                    "method_type": "charset_detector",
                    "auto_config": False,
                    "params": {
                        "time_dependent": True,
                        "timestamp_variable": "ts",
                        "timestamp_format": "%y%m%d %H%M%S",
                    },
                    "events": {
                        1: {
                            "inst": {
                                "params": {},
                                "variables": [{"pos": 0, "name": "v", "params": {}}],
                            }
                        }
                    },
                }
            }
        }
        detector = CharsetDetector(config=cfg, name="CharsetDetector")
        detector.train(_parser_record("081109 203615"))
        detector.train(_parser_record("081109 203645"))
        tracker = detector.persistency.get_events_data()[1].get_data()["v"]
        assert tracker.time_dependent is True
        assert len(tracker.timestamps) == len(tracker.change_series) == 2
        assert tracker.timestamps[1] - tracker.timestamps[0] == 30.0

    def test_time_dependent_fields_survive_auto_config_set_configuration(self):
        """set_configuration() reassigns self.config wholesale from a config
        dict generated with empty params (generate_detector_config only emits
        method_type/auto_config/params/events), so time_dependent,
        timestamp_variable and timestamp_format must be carried across that
        reassignment explicitly -- same as `persist` already is.

        auto_config defaults to True and core.py runs
        set_configuration() before train(), so this is the path every
        detector takes unless auto_config is explicitly disabled.
        """
        cfg = CharsetDetectorConfig(
            time_dependent=True,
            timestamp_variable="ts",
            timestamp_format="%y%m%d %H%M%S",
        )
        detector = CharsetDetector(config=cfg, name="CharsetDetector")
        assert detector.config.auto_config is True

        for _ in range(5):
            detector.configure(_parser_record("081109 203615"))
        detector.set_configuration()

        assert detector.config.time_dependent is True
        assert detector.config.timestamp_variable == "ts"
        assert detector.config.timestamp_format == "%y%m%d %H%M%S"
