"""Tests for the time-axis classification methods of the stability trackers."""

import math

from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.utils.persistency.data_structures.trackers.rle_list import RLEList
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    StabilityClassifier,
    SingleStabilityTracker,
    EventStabilityTracker,
    ClassificationMethods,
)
from tests.support.stability import BURSTY_TIMES, DIVERGENT_TIMES, feed_divergent

THRESHOLDS = [1.1, 0.3, 0.1, 0.01]  # same defaults ClassificationMethods uses


def make_index_classifier() -> StabilityClassifier:
    """Equal-index cuts -- the reference every fallback test compares to."""
    return StabilityClassifier(
        classification=ClassificationMethods(index=True, segment_thresholds=THRESHOLDS),
    )


def make_time_classifier() -> StabilityClassifier:
    """Equal-duration cuts -- what this file is about."""
    return StabilityClassifier(
        classification=ClassificationMethods(index=False, time=True, segment_thresholds=THRESHOLDS),
    )


# Divergence fixture: 3 changes up front, then a quiet tail of 37.
# In *time*, the changes span most of the observed window and the quiet
# tail is a burst compressed into ~0.04s at the end.
#
# The three change stamps are spaced so that each equal-duration quarter of the
# window holds exactly one occurrence (boundaries [0, 1, 2, 3, 40]), which is
# what puts a lone mean of 1.0 into a quarter whose threshold is 0.3.
DIVERGENT_SERIES = [True, True, True] + [False] * 37

BURSTY_SERIES = [True, False] * 20 + [False]

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
    def test_index_mode_is_stable_on_divergent_fixture(self):
        clf = make_index_classifier()
        # count segments of 10: means [0.3, 0, 0, 0] -> all below thresholds
        assert clf.is_stable(RLEList(DIVERGENT_SERIES)) is True

    def test_time_mode_is_unstable_on_divergent_fixture(self):
        clf = make_time_classifier()
        # time quarters put a lone change (mean 1.0) into segment 2 (thresh 0.3)
        assert clf.is_stable(RLEList(DIVERGENT_SERIES), timestamps=DIVERGENT_TIMES) is False

    def test_uniform_timestamps_match_index_mode(self):
        # N divisible by n_segments -> boundaries coincide exactly
        series = [True, False, False, True, False, False, False, False]
        ts = [float(i) for i in range(8)]
        clf_count = make_index_classifier()
        clf_count.is_stable(RLEList(series))
        clf_time = make_time_classifier()
        clf_time.is_stable(RLEList(series), timestamps=ts)
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_plain_list_path_supports_timestamps(self):
        clf = make_time_classifier()
        assert clf.is_stable(list(DIVERGENT_SERIES), timestamps=DIVERGENT_TIMES) is False

    def test_zero_span_falls_back_to_index_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_index_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_time_classifier()
        result = clf_time.is_stable(RLEList(series), timestamps=[5.0] * 8)
        assert result == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_length_mismatch_falls_back_to_index_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_index_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_time_classifier()
        assert clf_time.is_stable(RLEList(series), timestamps=[1.0, 2.0]) == expected

    def test_none_timestamp_entry_falls_back_to_index_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_index_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_time_classifier()
        ts = [0.0, 1.0, None, 3.0, 4.0, 5.0, 6.0, 7.0]
        assert clf_time.is_stable(RLEList(series), timestamps=ts) == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_nan_timestamp_entry_falls_back_to_index_mode(self):
        series = [True, False, False, False, False, False, False, False]
        clf_count = make_index_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_time_classifier()
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
        clf_count = make_index_classifier()
        assert clf_count.is_stable(RLEList(BURSTY_SERIES)) is False

        clf_time = make_time_classifier()
        assert clf_time.is_stable(RLEList(BURSTY_SERIES), timestamps=BURSTY_TIMES) is True
        assert clf_time.get_last_segment_means() == [0.5, 0.0, 0.0, 0.0]

    def test_empty_time_segment_scores_zero_on_plain_list_path(self):
        clf_time = make_time_classifier()
        assert clf_time.is_stable(list(BURSTY_SERIES), timestamps=BURSTY_TIMES) is True
        assert clf_time.get_last_segment_means() == [0.5, 0.0, 0.0, 0.0]

    def test_out_of_order_timestamps_fall_back_to_index_mode(self):
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

        clf_count = make_index_classifier()
        expected = clf_count.is_stable(RLEList(series))
        clf_time = make_time_classifier()
        assert clf_time.is_stable(RLEList(series), timestamps=unsorted_times) == expected
        assert clf_time.get_last_segment_means() == clf_count.get_last_segment_means()

    def test_sorted_timestamps_still_use_time_mode(self):
        """The monotonicity guard must not disable time mode for valid
        input."""
        clf = make_time_classifier()
        assert clf.is_stable(RLEList(DIVERGENT_SERIES), timestamps=DIVERGENT_TIMES) is False
        index = make_index_classifier()
        index.is_stable(RLEList(DIVERGENT_SERIES))
        assert clf.get_last_segment_means() != index.get_last_segment_means()

    def test_equal_timestamps_are_not_treated_as_out_of_order(self):
        """Duplicate stamps are non-decreasing, so they stay in time mode."""
        series = [True, False] * 20
        times = [float(i // 2) for i in range(40)]  # each stamp used twice
        clf = make_time_classifier()
        assert clf.is_stable(RLEList(series), timestamps=times) is False
        assert not any(math.isnan(mean) for mean in clf.get_last_segment_means())

    def test_list_and_rle_agree_on_ragged_length(self):
        """13 items over 4 segments: both paths must cut identically."""
        series = [True, False, True] + [False] * 10
        clf_list = make_index_classifier()
        clf_list.is_stable(list(series))
        clf_rle = make_index_classifier()
        clf_rle.is_stable(RLEList(series))
        assert clf_list.get_last_segment_means() == clf_rle.get_last_segment_means()


def feed_churn(tracker: SingleStabilityTracker) -> None:
    """30 new values one second apart, then a repeated value over ~17 min."""
    for value, ts in zip(CHURN_VALUES, CHURN_TIMES):
        tracker.add_value(value, timestamp=ts)


def feed_agreeing(tracker: SingleStabilityTracker) -> None:
    """One change up front, then a settled value, evenly spaced."""
    for value, ts in zip(AGREE_VALUES, AGREE_TIMES):
        tracker.add_value(value, timestamp=ts)


_TIME = ClassificationMethods(index=False, time=True)


class TestIndexAndTimeTogether:
    """Index + time is STABLE only when both methods agree."""

    def test_rejects_when_only_time_is_unstable(self):
        count_mode = SingleStabilityTracker()
        feed_divergent(count_mode)
        assert count_mode.classify().type == "STABLE"

        time_mode = SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True))
        feed_divergent(time_mode)
        assert time_mode.classify().type == "UNSTABLE"

        both_mode = SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True))
        feed_divergent(both_mode)
        assert both_mode.classify().type == "UNSTABLE"

    def test_rejects_when_only_count_is_unstable(self):
        """The opposite direction: proves neither pass is dead code."""
        count_mode = SingleStabilityTracker()
        feed_churn(count_mode)
        assert count_mode.classify().type == "UNSTABLE"

        time_mode = SingleStabilityTracker(classification=ClassificationMethods(index=False, time=True))
        feed_churn(time_mode)
        assert time_mode.classify().type == "STABLE"

        both_mode = SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True))
        feed_churn(both_mode)
        assert both_mode.classify().type == "UNSTABLE"

    def test_accepts_when_both_agree(self):
        """`both` must not be vacuously strict."""
        modes = {
            "index": ClassificationMethods(index=True),
            "time": ClassificationMethods(index=False, time=True),
            "both": ClassificationMethods(index=True, time=True),
        }
        for mode, methods in modes.items():
            tracker = SingleStabilityTracker(classification=methods)
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
        both_mode = SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True))
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
        tracker = SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True))
        feed_churn(tracker)
        classification = tracker.classify()
        assert classification.type == "UNSTABLE"
        reason = classification.reason
        assert "index: means [1.0, 1.0, 1.0, 0.0]" in reason
        assert "time: means [0.9375, 0.0, 0.0, 0.0]" in reason

    def test_round_trip_preserves_both_mode(self):
        tracker = SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True))
        feed_churn(tracker)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.classification == ClassificationMethods(index=True, time=True)
        assert restored.timestamps == tracker.timestamps
        assert restored.classify().type == "UNSTABLE"

    def test_stability_note_is_not_persisted(self):
        tracker = SingleStabilityTracker(classification=ClassificationMethods(index=True, time=True))
        feed_agreeing(tracker)
        tracker.classify()
        assert "_stability_note" not in tracker.to_state()

    def test_config_accepts_both_and_reaches_trackers(self):
        # classification only shapes the configure-phase persistency (see
        # TestClassificationConfigWiring.test_flag_reaches_per_variable_trackers).
        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.auto_config_params.classification = ClassificationMethods(
            index=True, time=True
        )
        rebuilt = CharsetDetector(
            config=configured.config.to_dict(method_id="CharsetDetector")
        )
        block = rebuilt.auto_conf_persistency.event_struct.data_kwargs["classification"]
        assert ClassificationMethods(**block).enabled == ("index", "time")

    def test_event_tracker_propagates_both(self):
        event_tracker = EventStabilityTracker(
            classification=ClassificationMethods(index=True, time=True)
        )
        event_tracker.add_data({"var1": "a"}, timestamp=1.0)
        event_tracker.add_data({"var1": "b"}, timestamp=2.0)
        single = event_tracker.get_data()["var1"]
        assert single.classification == ClassificationMethods(index=True, time=True)
        assert single.timestamps == [1.0, 2.0]
