"""Tests for the slope classification methods of the stability trackers.

The slope is the change centroid: the mean position of the changes,
measured against the midpoint of the range those changes could occupy
and scaled by its half-span, so it lands in [-0.5, +0.5]. Index 0 is
excluded -- the first value is always recorded as a change, and keeping
it would drag every variable negative, a perfectly static one included.

`slope_index` measures position on the index axis, `slope_time` on
normalized wall-clock time. With evenly spaced timestamps the two agree
exactly; that correspondence is what lets them share one threshold.
"""

import numpy as np
import pytest

from detectmatelibrary.utils.persistency.data_structures.trackers.rle_list import RLEList
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    StabilityClassifier,
    ClassificationMethods,
)
from tests.support.stability import EARLY, LATE_BUT_PASSING


def make_classifier(**kwargs) -> StabilityClassifier:
    return StabilityClassifier(**kwargs)


class TestSlopeIndexAxis:
    def test_hand_checked_values(self):
        clf = make_classifier()
        # n=5, changes at 1 and 2 -> p_bar 1.5, midpoint 2.5, half-span 3
        assert clf.slope(RLEList([True, True, True, False, False])) == -1 / 3
        # mirror image, changes at 3 and 4 -> p_bar 3.5
        assert clf.slope(RLEList([True, False, False, True, True])) == 1 / 3

    def test_no_changes_after_the_first_hits_the_floor(self):
        assert make_classifier().slope(RLEList([True] + [False] * 39)) == -0.5

    def test_changing_every_step_is_perfectly_uniform(self):
        assert make_classifier().slope(RLEList([True] * 40)) == 0.0

    def test_too_short_to_have_a_span(self):
        clf = make_classifier()
        assert clf.slope(RLEList([True, False])) == 0.0
        assert clf.slope(RLEList([])) == 0.0

    def test_stays_within_bounds(self):
        clf, rng = make_classifier(), np.random.default_rng(11)
        for _ in range(200):
            n = int(rng.integers(3, 300))
            f = [True] + list(rng.random(n - 1) < rng.random())
            assert -0.5 <= clf.slope(RLEList(f)) <= 0.5

    def test_rle_and_plain_list_agree(self):
        clf, rng = make_classifier(), np.random.default_rng(12)
        for _ in range(200):
            n = int(rng.integers(3, 300))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            assert clf.slope(RLEList(f)) == clf.slope(f)

    def test_sign_always_matches_the_least_squares_slope(self):
        """k_OLS = k * 12m / n(n-1), a strictly positive factor -- so a polyfit
        over the same series can never disagree on the verdict."""
        clf, rng = make_classifier(), np.random.default_rng(13)
        for _ in range(200):
            n = int(rng.integers(4, 300))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            if not any(f[1:]):
                continue
            slope = np.polyfit(np.arange(1, n), np.asarray(f[1:], dtype=float), 1)[0]
            assert np.sign(round(clf.slope(RLEList(f)), 12)) == np.sign(round(slope, 12))


class TestSlopeTimeAxis:
    def test_evenly_spaced_stamps_reproduce_the_index_axis(self):
        """The property that lets both slope methods share one threshold."""
        clf, rng = make_classifier(), np.random.default_rng(14)
        for _ in range(100):
            n = int(rng.integers(3, 200))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            stamps = [float(i) for i in range(n)]
            assert clf.slope(RLEList(f), stamps) == pytest.approx(clf.slope(RLEList(f)))

    def test_hand_checked_value_on_a_stretched_span(self):
        """Changes at indices 1 and 2 of five, with the tail an eternity later.

        u = 1/101, 2/101 -> u_bar 0.0148515; u_first = 1/101 = 0.0099010
        k = (0.0148515 - (0.0099010 + 1) / 2) / (1 - 0.0099010) = -0.495
        The same series on evenly spaced stamps gives -1/3.
        """
        clf = make_classifier()
        f = RLEList([True, True, True, False, False])
        assert clf.slope(f, [0.0, 1.0, 2.0, 100.0, 101.0]) == pytest.approx(-0.495)
        assert clf.slope(f, [0.0, 1.0, 2.0, 3.0, 4.0]) == pytest.approx(-1 / 3)

    def test_axes_can_disagree_in_sign(self):
        """The case that motivates having both slope methods.

        [T,F,F,F,F,F,F,T,T,F] with the whole tail one long silence: the
        changes sit late in *record count* (index +0.313) but they all
        happened in the first moments of a long observation window (time
        -0.493). Only the time axis sees that the variable settled.
        """
        clf = make_classifier()
        f = RLEList([True] + [False] * 6 + [True, True, False])
        stamps = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 1000.0]
        assert clf.slope(f) == pytest.approx(0.3125)
        assert clf.slope(f, stamps) == pytest.approx(-0.4935, abs=1e-4)

    def test_changes_late_in_the_span_score_positive(self):
        clf = make_classifier()
        f = RLEList([True, False, False, True, True])
        assert clf.slope(f, [0.0, 1.0, 2.0, 100.0, 101.0]) > 0.4

    def test_no_changes_after_the_first_hits_the_floor(self):
        clf = make_classifier()
        stamps = [float(i) for i in range(40)]
        assert clf.slope(RLEList([True] + [False] * 39), stamps) == -0.5

    def test_stays_within_bounds(self):
        clf, rng = make_classifier(), np.random.default_rng(15)
        for _ in range(200):
            n = int(rng.integers(3, 300))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            stamps = list(np.cumsum(rng.random(n)))
            assert -0.5 <= clf.slope(RLEList(f), stamps) <= 0.5

    def test_rle_and_plain_list_agree(self):
        clf, rng = make_classifier(), np.random.default_rng(16)
        for _ in range(100):
            n = int(rng.integers(3, 200))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            stamps = list(np.cumsum(rng.random(n)))
            assert clf.slope(RLEList(f), stamps) == clf.slope(f, stamps)


class TestSlopeTimeFallsBackToIndex:
    """Time-aware classification is best-effort: it degrades to the index
    axis rather than failing a run or passing unconditionally."""

    SERIES = RLEList([True, True, True, False, False])

    def index_value(self):
        return make_classifier().slope(self.SERIES)

    def test_no_timestamps(self):
        assert make_classifier().slope(self.SERIES, None) == self.index_value()

    def test_length_mismatch(self):
        assert make_classifier().slope(self.SERIES, [0.0, 1.0]) == self.index_value()

    def test_zero_span(self):
        stamps = [7.0] * 5
        assert make_classifier().slope(self.SERIES, stamps) == self.index_value()

    def test_out_of_order(self):
        stamps = [0.0, 5.0, 2.0, 6.0, 7.0]
        assert make_classifier().slope(self.SERIES, stamps) == self.index_value()

    def test_non_finite_entry(self):
        stamps = [0.0, 1.0, float("nan"), 3.0, 4.0]
        assert make_classifier().slope(self.SERIES, stamps) == self.index_value()

    def test_none_entry(self):
        stamps = [0.0, 1.0, None, 3.0, 4.0]
        assert make_classifier().slope(self.SERIES, stamps) == self.index_value()

    def test_zero_achievable_range(self):
        """t_1 == t_last: every countable position shares one instant, so the
        time axis has no range to normalize against."""
        stamps = [0.0, 9.0, 9.0, 9.0, 9.0]
        assert make_classifier().slope(self.SERIES, stamps) == self.index_value()


class TestSlopeReportsItsAxis:
    def test_time_axis_when_usable(self):
        clf = make_classifier()
        _, axis = clf._slope(RLEList([True, True, False, False]), [0.0, 1.0, 2.0, 3.0])
        assert axis == "time"

    def test_index_axis_on_fallback(self):
        clf = make_classifier()
        _, axis = clf._slope(RLEList([True, True, False, False]), None)
        assert axis == "index"


# Fixture reused from test_time_dependent_stability.py: 30 fresh values one
# second apart, then the same value repeated 10 times spread over ~17 minutes.
#   index  -> means [1.0, 1.0, 1.0, 0.0]   -> UNSTABLE
#   time   -> means [0.938, 0.0, 0.0, 0.0] -> STABLE
#   slopes -> -0.132 (index), -0.486 (time) -> both STABLE
# The one fixture that splits 3-1, which is what makes majority testable at
# four enabled methods.
CHURN_SERIES = [True] * 30 + [False] * 10
CHURN_TIMES = [float(i) for i in range(30)] + [100.0 * (i + 1) for i in range(10)]

UNIFORM_400 = [float(i) for i in range(400)]


def methods(**kwargs) -> ClassificationMethods:
    """A method block with every default overridable, index included."""
    return ClassificationMethods(**{"index": False, **kwargs})


class TestVerdicts:
    def test_only_enabled_methods_appear_in_block_order(self):
        clf = make_classifier(classification=methods(slope_time=True, index=True))
        assert list(clf.verdicts(RLEList(LATE_BUT_PASSING), UNIFORM_400)) == [
            "index", "slope_time",
        ]

    def test_late_but_passing_splits_segments_from_slope(self):
        clf = make_classifier(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        assert clf.verdicts(RLEList(LATE_BUT_PASSING)) == {
            "index": True, "slope_index": False,
        }

    def test_churn_fixture_splits_three_to_one(self):
        clf = make_classifier(classification=ClassificationMethods(
            index=True, time=True, slope_index=True, slope_time=True,
        ))
        assert clf.verdicts(RLEList(CHURN_SERIES), CHURN_TIMES) == {
            "index": False, "time": True, "slope_index": True, "slope_time": True,
        }

    def test_a_slope_method_can_stand_alone(self):
        clf = make_classifier(classification=methods(slope_index=True))
        assert clf.verdicts(RLEList(EARLY)) == {"slope_index": True}

    def test_standing_alone_skips_the_segment_means(self):
        """With no segment-threshold method enabled the means are never
        computed, so the classifier must not report stale ones."""
        clf = make_classifier(classification=methods(slope_index=True))
        clf.verdicts(RLEList(EARLY))
        assert clf.get_last_segment_means() == []

    def test_empty_series_is_stable_under_every_method(self):
        clf = make_classifier(classification=ClassificationMethods(
            index=True, time=True, slope_index=True, slope_time=True,
        ))
        assert clf.verdicts(RLEList([])) == {
            "index": True, "time": True, "slope_index": True, "slope_time": True,
        }

    def test_slope_threshold_is_read_from_the_block(self):
        late = RLEList(LATE_BUT_PASSING)  # centroid +0.028
        strict = make_classifier(classification=methods(slope_index=True))
        assert strict.verdicts(late) == {"slope_index": False}
        loose = make_classifier(
            classification=methods(slope_index=True, slope_threshold=0.1)
        )
        assert loose.verdicts(late) == {"slope_index": True}


class TestDecisionRule:
    """Consensus and majority agree at one and two enabled methods and diverge
    at three and four.

    Ties resolve to UNSTABLE.
    """

    @pytest.mark.parametrize(
        "verdicts, consensus, majority",
        [
            ({"a": True}, True, True),
            ({"a": False}, False, False),
            ({"a": True, "b": True}, True, True),
            ({"a": True, "b": False}, False, False),          # 1-1 tie
            ({"a": True, "b": True, "c": True}, True, True),
            ({"a": True, "b": True, "c": False}, False, True),  # 2/3
            ({"a": True, "b": False, "c": False}, False, False),
            ({"a": True, "b": True, "c": True, "d": True}, True, True),
            ({"a": True, "b": True, "c": True, "d": False}, False, True),  # 3/4
            ({"a": True, "b": True, "c": False, "d": False}, False, False),  # 2-2 tie
        ],
    )
    def test_table(self, verdicts, consensus, majority):
        for rule, expected in (("consensus", consensus), ("majority", majority)):
            clf = make_classifier(
                classification=ClassificationMethods(decision=rule)
            )
            assert clf.decide(verdicts) is expected

    def test_majority_rescues_the_three_to_one_fixture(self):
        block = dict(index=True, time=True, slope_index=True, slope_time=True)
        strict = make_classifier(
            classification=ClassificationMethods(**block, decision="consensus")
        )
        lenient = make_classifier(
            classification=ClassificationMethods(**block, decision="majority")
        )
        assert strict.is_stable(RLEList(CHURN_SERIES), CHURN_TIMES) is False
        assert lenient.is_stable(RLEList(CHURN_SERIES), CHURN_TIMES) is True

    def test_two_two_tie_stays_unstable(self):
        block = dict(index=True, time=True, slope_index=True, slope_time=True)
        lenient = make_classifier(
            classification=ClassificationMethods(**block, decision="majority")
        )
        # index/time STABLE, both slopes UNSTABLE (centroid +0.028)
        assert lenient.is_stable(RLEList(LATE_BUT_PASSING), UNIFORM_400) is False


class TestFallbackDoubleCount:
    """A fallen-back method still casts its vote.

    Dropping it instead would make the enabled count vary per variable,
    so majority would mean something different for each one.
    """

    def test_both_slopes_vote_the_same_way_without_stamps(self):
        clf = make_classifier(
            classification=methods(slope_index=True, slope_time=True)
        )
        assert clf.verdicts(RLEList(LATE_BUT_PASSING), None) == {
            "slope_index": False, "slope_time": False,
        }

    def test_the_details_name_the_axis_actually_used(self):
        clf = make_classifier(
            classification=methods(slope_index=True, slope_time=True)
        )
        clf.verdicts(RLEList(LATE_BUT_PASSING), None)
        assert "index axis" in clf.get_last_details()["slope_time"]


class TestDetails:
    def test_segment_method_reports_means_and_thresholds(self):
        clf = make_classifier(classification=ClassificationMethods(index=True))
        clf.verdicts(RLEList(EARLY))
        detail = clf.get_last_details()["index"]
        assert "index:" in detail and "STABLE" in detail
        assert str(ClassificationMethods().segment_thresholds) in detail

    def test_slope_method_reports_the_centroid_and_threshold(self):
        clf = make_classifier(classification=methods(slope_index=True))
        clf.verdicts(RLEList(LATE_BUT_PASSING))
        detail = clf.get_last_details()["slope_index"]
        assert "slope_index:" in detail and "UNSTABLE" in detail
        assert "-0.05" in detail and "index axis" in detail

    def test_details_cover_exactly_the_enabled_methods(self):
        clf = make_classifier(classification=ClassificationMethods(
            index=True, slope_time=True,
        ))
        verdicts = clf.verdicts(RLEList(EARLY), UNIFORM_400)
        assert set(clf.get_last_details()) == set(verdicts)
