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
from pydantic import ValidationError

from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.common.variable_detector import VariableAutoConfigParams
from detectmatelibrary.utils.persistency.rle_list import RLEList
from detectmatelibrary.utils.persistency.event_data_structures.trackers import (
    StabilityClassifier,
    SingleStabilityTracker,
    EventStabilityTracker,
    ClassificationMethods,
)

THRESHOLDS = [1.1, 0.3, 0.1, 0.01]  # same defaults SingleStabilityTracker uses


def make_classifier(**kwargs) -> StabilityClassifier:
    return StabilityClassifier(segment_thresholds=THRESHOLDS, **kwargs)


def series(n: int, *change_ranges: range) -> list:
    """A change series of length n with index 0 True plus the given ranges."""
    out = [False] * n
    out[0] = True
    for r in change_ranges:
        for i in r:
            out[i] = True
    return out


def feed(tracker: SingleStabilityTracker, change_series) -> None:
    """Drive a tracker so its change_series matches: fresh value on each
    True, a repeat otherwise."""
    seen = 0
    for changed in change_series:
        if changed:
            seen += 1
        tracker.add_value(f"v{seen}")


# The flag only bites where the segment thresholds do not already imply an
# early centroid, and that gap opens up with series length. Over 400 samples
# the quarters are wide enough to hold 29 changes under threshold 0.3 and 9
# under 0.1, so a variable can pass every segment test with its changes still
# sitting *late*: quarter means [0.01, 0.29, 0.09, 0.0] -> STABLE, centroid
# +0.028 -> not declining.
LATE_BUT_PASSING = series(400, range(171, 200), range(291, 300))

# Same length, changes up front: STABLE under the segment thresholds and
# strongly declining (centroid -0.464), so the flag leaves it alone.
EARLY = series(400, range(1, 31))

# Segment-UNSTABLE (quarter 1 mean 0.51 > 0.3) but strongly declining. The
# flag is a conjunct, so it can never rescue this one.
DENSE_EARLY = series(400, range(1, 151))


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


class TestSlopeVerdictsOnTrackers:
    def test_off_by_default_changes_nothing(self):
        tracker = SingleStabilityTracker()
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.classification.enabled == ("index",)
        assert tracker.classify().type == "STABLE"

    def test_slope_index_flips_a_late_but_passing_variable(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.classify().type == "UNSTABLE"

    def test_slope_index_leaves_an_early_variable_alone(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        feed(tracker, EARLY)
        assert tracker.classify().type == "STABLE"

    def test_consensus_can_only_tighten_never_loosen(self):
        off = SingleStabilityTracker()
        on = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        feed(off, DENSE_EARLY)
        feed(on, DENSE_EARLY)
        # strongly declining (-0.313) but index-UNSTABLE -> stays UNSTABLE
        assert off.classify().type == "UNSTABLE"
        assert on.classify().type == "UNSTABLE"

    def test_slope_index_can_stand_alone(self):
        """DENSE_EARLY is index-UNSTABLE but strongly declining.

        With the segment methods off, only the centroid decides -- and
        it says stable.
        """
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=False, slope_index=True)
        )
        feed(tracker, DENSE_EARLY)
        assert tracker.classify().type == "STABLE"

    def test_threshold_is_configurable(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.classify().type == "UNSTABLE"
        # centroid is +0.028; a threshold above it lets the variable through
        tracker.classification = ClassificationMethods(
            index=True, slope_index=True, slope_threshold=0.1
        )
        assert tracker.classify().type == "STABLE"

    def test_reason_names_every_enabled_method_and_the_decision(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        feed(tracker, EARLY)
        reason = tracker.classify().reason
        assert "index:" in reason and "slope_index:" in reason
        assert "decision=consensus (2/2)" in reason

    def test_reason_omits_methods_that_are_off(self):
        tracker = SingleStabilityTracker()
        feed(tracker, EARLY)
        reason = tracker.classify().reason
        assert "slope_index:" not in reason and "time:" not in reason

    def test_early_classify_reasons_are_untouched(self):
        """STATIC / RANDOM / INSUFFICIENT_DATA are decided before any method is
        consulted, so no method setting can reach them."""
        static = SingleStabilityTracker(
            classification=ClassificationMethods(index=False, slope_time=True)
        )
        for _ in range(10):
            static.add_value("a", timestamp=1.0)
        assert static.classify().type == "STATIC"

        short = SingleStabilityTracker()
        short.add_value("a")
        assert short.classify().type == "INSUFFICIENT_DATA"


class TestTimestampCollection:
    def test_index_only_collects_nothing(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("a", timestamp=1.0)
        assert tracker.timestamps == []

    def test_slope_index_only_collects_nothing(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=False, slope_index=True)
        )
        tracker.add_value("a", timestamp=1.0)
        assert tracker.timestamps == []

    def test_slope_time_collects_stamps(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=False, slope_time=True)
        )
        tracker.add_value("a", timestamp=1.0)
        tracker.add_value("b", timestamp=2.0)
        assert tracker.timestamps == [1.0, 2.0]

    def test_slope_time_without_stamps_falls_back_to_the_index_axis(self):
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=False, slope_time=True)
        )
        feed(tracker, LATE_BUT_PASSING)  # feed() passes no timestamps
        assert tracker.timestamps == []
        assert "index axis" in tracker.classify().reason


class TestClassificationIsSwappable:
    """The parent repo's notebooks get several verdicts from one ingest by
    reassigning this between classify() calls."""

    def test_reassignment_changes_the_verdict(self):
        tracker = SingleStabilityTracker()
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.classify().type == "STABLE"
        tracker.classification = ClassificationMethods(index=True, slope_index=True)
        assert tracker.classify().type == "UNSTABLE"

    def test_the_classifier_cannot_drift_from_the_tracker(self):
        """One property over one owner -- not two attributes to keep in
        sync."""
        tracker = SingleStabilityTracker()
        tracker.classification = ClassificationMethods(index=False, time=True)
        assert tracker.stability_classifier.classification is tracker.classification
        assert tracker.classification.needs_timestamps is True

    def test_accepts_a_plain_dict(self):
        """State and config both deliver the block as a dict."""
        tracker = SingleStabilityTracker(classification={"index": True, "time": True})
        assert tracker.classification == ClassificationMethods(index=True, time=True)

    def test_setter_accepts_a_plain_dict(self):
        """The setter coerces too, not just the constructor."""
        tracker = SingleStabilityTracker()
        tracker.classification = {"index": True, "slope_index": True, "slope_threshold": 0.2}
        assert tracker.stability_classifier.classification == ClassificationMethods(
            index=True, slope_index=True, slope_threshold=0.2
        )
        assert tracker.classification == ClassificationMethods(
            index=True, slope_index=True, slope_threshold=0.2
        )


class TestStatePersistence:
    def test_round_trip_preserves_the_block(self):
        tracker = SingleStabilityTracker(classification=ClassificationMethods(
            index=True, slope_index=True, slope_threshold=-0.2, decision="majority",
        ))
        feed(tracker, EARLY)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.classification == tracker.classification
        assert restored.classify().type == tracker.classify().type

    def test_state_is_msgpack_plain(self):
        """to_state() must be msgpack-compatible: a pydantic model is not."""
        state = SingleStabilityTracker().to_state()
        assert isinstance(state["classification"], dict)
        assert set(state["classification"]) == {
            "index", "time", "slope_index", "slope_time", "slope_threshold", "decision",
        }

    def test_old_keys_are_gone_from_state(self):
        state = SingleStabilityTracker().to_state()
        for key in ("segmentation", "require_declining", "incline_threshold"):
            assert key not in state

    def test_the_note_is_not_persisted(self):
        tracker = SingleStabilityTracker()
        feed(tracker, EARLY)
        tracker.classify()
        assert "_stability_note" not in tracker.to_state()

    def test_event_tracker_propagates_the_block(self):
        event_tracker = EventStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        event_tracker.add_data({"var1": "a"})
        event_tracker.add_data({"var1": "b"})
        assert event_tracker.get_data()["var1"].classification.enabled == (
            "index", "slope_index",
        )

    def test_event_tracker_dump_load_preserves_the_block(self):
        event_tracker = EventStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        event_tracker.add_data({"var1": "a"})
        event_tracker.add_data({"var1": "b"})
        restored = EventStabilityTracker.load(
            event_tracker.dump(),
            classification={"index": True, "slope_index": True},
        )
        assert restored.get_data()["var1"].classification.enabled == (
            "index", "slope_index",
        )


class TestLegacyStateMigration:
    """Snapshots written before this change must keep loading.

    This is the one place the old names survive.
    """

    def legacy_state(self, **overrides):
        state = SingleStabilityTracker().to_state()
        del state["classification"]
        state.update(overrides)
        return state

    def test_no_stability_keys_at_all(self):
        restored = SingleStabilityTracker.from_state(self.legacy_state())
        assert restored.classification == ClassificationMethods()

    def test_segmentation_count(self):
        restored = SingleStabilityTracker.from_state(
            self.legacy_state(segmentation="count")
        )
        assert restored.classification.enabled == ("index",)

    def test_segmentation_time_means_time_alone(self):
        restored = SingleStabilityTracker.from_state(
            self.legacy_state(segmentation="time")
        )
        assert restored.classification.enabled == ("time",)

    def test_segmentation_both(self):
        restored = SingleStabilityTracker.from_state(
            self.legacy_state(segmentation="both")
        )
        assert restored.classification.enabled == ("index", "time")

    def test_require_declining_becomes_slope_index(self):
        restored = SingleStabilityTracker.from_state(
            self.legacy_state(segmentation="count", require_declining=True)
        )
        assert restored.classification.enabled == ("index", "slope_index")

    def test_incline_threshold_becomes_slope_threshold(self):
        restored = SingleStabilityTracker.from_state(
            self.legacy_state(
                segmentation="count", require_declining=True, incline_threshold=-0.25
            )
        )
        assert restored.classification.slope_threshold == -0.25

    def test_legacy_states_always_decide_by_consensus(self):
        restored = SingleStabilityTracker.from_state(
            self.legacy_state(segmentation="both", require_declining=True)
        )
        assert restored.classification.decision == "consensus"
        assert restored.classification.enabled == ("index", "time", "slope_index")

    def test_legacy_state_without_add_value_keys_still_loads(self):
        """Old enough to predate add_value_fn as well."""
        state = self.legacy_state(segmentation="both")
        del state["add_value_fn"], state["detector_config"]
        restored = SingleStabilityTracker.from_state(state)
        assert restored.classification.enabled == ("index", "time")

    def test_fed_tracker_with_deleted_classification_key_classifies_correctly(self):
        """End-to-end: legacy snapshot with real observations restores and
        classifies correctly. This verifies the migration works not just for
        config translation but for the full state round-trip."""
        tracker = SingleStabilityTracker()
        feed(tracker, EARLY)
        state = tracker.to_state()
        del state["classification"]
        restored = SingleStabilityTracker.from_state(state)
        assert restored.classify().type == "STABLE"


class TestConfigWiring:
    def test_block_reaches_per_variable_trackers(self):
        # CharsetDetector's `config` default is a shared mutable instance, so
        # pass explicit fresh configs (see test_time_dependent_stability.py).
        #
        # classification only shapes the configure-phase persistency: the
        # trained persistency is read by _check_variable, which never calls
        # classify(), so it never receives classification kwargs at all.
        default = CharsetDetector(config=CharsetDetectorConfig())
        assert default.persistency.event_data_kwargs.get("classification") is None

        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.auto_config_params.classification = ClassificationMethods(
            index=True, slope_index=True
        )
        rebuilt = CharsetDetector(config=configured.config.to_dict(method_id="CharsetDetector"))
        block = rebuilt.auto_conf_persistency.event_data_kwargs["classification"]
        assert ClassificationMethods(**block).enabled == ("index", "slope_index")

    def test_default_block_is_not_forwarded(self):
        """Forwarding the default would be noise; the tracker already has
        it."""
        default = CharsetDetector(config=CharsetDetectorConfig())
        assert "classification" not in (default.auto_conf_persistency.event_data_kwargs or {})

    def test_config_field_round_trips(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.classification = ClassificationMethods(
            index=False, slope_time=True, decision="majority"
        )
        restored = type(detector.config).from_dict(
            detector.config.to_dict(method_id="CharsetDetector"), "CharsetDetector"
        )
        assert restored.auto_config_params.classification.enabled == ("slope_time",)
        assert restored.auto_config_params.classification.decision == "majority"

    def test_survives_auto_config(self):
        """set_configuration() writes only config.events and flips
        config.auto_config to False -- it never touches auto_config_params, so
        operator settings survive because nothing overwrites them."""
        detector = CharsetDetector(config=CharsetDetectorConfig(
            auto_config=True,
            auto_config_params=VariableAutoConfigParams(
                classification=ClassificationMethods(index=True, slope_index=True),
                use_static_vars=False,
            ),
        ))
        detector.set_configuration()
        assert detector.config.auto_config_params.classification.enabled == (
            "index", "slope_index",
        )
        assert detector.config.auto_config_params.use_static_vars is False

    def test_index_axis_methods_pull_in_no_timestamp_requirement(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.auto_config_params.classification = ClassificationMethods(
            index=True, slope_index=True
        )
        rebuilt = CharsetDetector(config=detector.config.to_dict(method_id="CharsetDetector"))
        assert "classification" not in (rebuilt.persistency.event_data_kwargs or {})

        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(index=True, slope_index=True)
        )
        tracker.add_value("a", timestamp=1.0)
        assert tracker.timestamps == []


class TestOldConfigFieldsAreRejected:
    """Clean break: AutoConfigParams sets extra='forbid', so the old
    spellings raise instead of being silently ignored."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"segmentation": "both"},
            {"require_declining": True},
            {"incline_threshold": -0.25},
        ],
    )
    def test_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            VariableAutoConfigParams(**kwargs)


def test_slope_threshold_reaches_the_classifier():
    """The threshold is configuration, not a constant buried in the
    classifier."""
    from detectmatelibrary.detectors.new_value_detector import (
        NewValueDetector,
        NewValueDetectorConfig,
    )

    detector = NewValueDetector(
        name="NewValueDetector",
        config=NewValueDetectorConfig(
            auto_config_params=VariableAutoConfigParams(
                classification=ClassificationMethods(
                    index=True, slope_index=True, slope_threshold=-0.25
                ),
            ),
        ),
    )
    persistency = detector.auto_conf_persistency
    tracker = persistency.event_data_class(**persistency.event_data_kwargs)
    single = tracker.single_tracker_type()
    assert single.classification.enabled == ("index", "slope_index")
    assert single.stability_classifier.classification.slope_threshold == -0.25


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
        assert str(THRESHOLDS) in detail

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
