"""Tests for the require_declining option of the stability trackers.

The incline is the change centroid: the mean position of the changes,
measured against the midpoint of the series and scaled by the half-span,
so it lands in [-0.5, +0.5]. Index 0 is excluded -- the first value is
always recorded as a change, and keeping it would drag every variable
negative, a perfectly static one included.
"""

import numpy as np

from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.utils.persistency.rle_list import RLEList
from detectmatelibrary.utils.persistency.event_data_structures.trackers import (
    StabilityClassifier,
    SingleStabilityTracker,
    EventStabilityTracker,
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


class TestInclineStatistic:
    def test_hand_checked_values(self):
        clf = make_classifier()
        # n=5, changes at 1 and 2 -> p_bar 1.5, midpoint 2.5, half-span 3
        assert clf.incline(RLEList([True, True, True, False, False])) == -1 / 3
        # mirror image, changes at 3 and 4 -> p_bar 3.5
        assert clf.incline(RLEList([True, False, False, True, True])) == 1 / 3

    def test_no_changes_after_the_first_hits_the_floor(self):
        clf = make_classifier()
        assert clf.incline(RLEList([True] + [False] * 39)) == -0.5

    def test_changing_every_step_is_perfectly_uniform(self):
        clf = make_classifier()
        assert clf.incline(RLEList([True] * 40) ) == 0.0

    def test_too_short_to_have_a_span(self):
        clf = make_classifier()
        assert clf.incline(RLEList([True, False])) == 0.0
        assert clf.incline(RLEList([])) == 0.0

    def test_stays_within_bounds(self):
        clf, rng = make_classifier(), np.random.default_rng(11)
        for _ in range(200):
            n = int(rng.integers(3, 300))
            f = [True] + list(rng.random(n - 1) < rng.random())
            assert -0.5 <= clf.incline(RLEList(f)) <= 0.5

    def test_rle_and_plain_list_agree(self):
        clf, rng = make_classifier(), np.random.default_rng(12)
        for _ in range(200):
            n = int(rng.integers(3, 300))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            assert clf.incline(RLEList(f)) == clf.incline(f)

    def test_sign_always_matches_the_least_squares_slope(self):
        """k_OLS = k * 12m / n(n-1), a strictly positive factor -- so a
        polyfit over the same series can never disagree on the verdict."""
        clf, rng = make_classifier(), np.random.default_rng(13)
        for _ in range(200):
            n = int(rng.integers(4, 300))
            f = [True] + list(bool(v) for v in rng.random(n - 1) < rng.random())
            if not any(f[1:]):
                continue
            slope = np.polyfit(np.arange(1, n), np.asarray(f[1:], dtype=float), 1)[0]
            assert np.sign(round(clf.incline(RLEList(f)), 12)) == np.sign(round(slope, 12))


class TestRequireDecliningVerdicts:
    def test_off_by_default_changes_nothing(self):
        tracker = SingleStabilityTracker()
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.require_declining is False
        assert tracker.classify().type == "STABLE"

    def test_on_flips_a_late_but_passing_variable(self):
        tracker = SingleStabilityTracker(require_declining=True)
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.classify().type == "UNSTABLE"

    def test_on_leaves_an_early_variable_alone(self):
        tracker = SingleStabilityTracker(require_declining=True)
        feed(tracker, EARLY)
        assert tracker.classify().type == "STABLE"

    def test_can_only_tighten_never_loosen(self):
        off, on = SingleStabilityTracker(), SingleStabilityTracker(require_declining=True)
        feed(off, DENSE_EARLY)
        feed(on, DENSE_EARLY)
        # strongly declining (-0.313) but segment-UNSTABLE -> stays UNSTABLE
        assert off.classify().type == "UNSTABLE"
        assert on.classify().type == "UNSTABLE"

    def test_threshold_is_configurable(self):
        tracker = SingleStabilityTracker(require_declining=True)
        feed(tracker, LATE_BUT_PASSING)
        assert tracker.classify().type == "UNSTABLE"
        # centroid is +0.028; a threshold above it lets the variable through
        tracker.stability_classifier.incline_threshold = 0.1
        assert tracker.classify().type == "STABLE"

    def test_reason_carries_the_centroid_only_when_enabled(self):
        on = SingleStabilityTracker(require_declining=True)
        feed(on, EARLY)
        assert "change centroid" in on.classify().reason

        off = SingleStabilityTracker()
        feed(off, EARLY)
        assert "change centroid" not in off.classify().reason

    def test_composes_with_both_segmentation(self):
        tracker = SingleStabilityTracker(segmentation="both", require_declining=True)
        for i, changed in enumerate(LATE_BUT_PASSING):
            tracker.add_value(f"v{sum(LATE_BUT_PASSING[:i + 1])}", timestamp=float(i))
        assert tracker.classify().type == "UNSTABLE"
        reason = tracker.classify().reason
        assert "count" in reason and "time" in reason and "change centroid" in reason


class TestRequireDecliningPlumbing:
    def test_state_round_trip(self):
        tracker = SingleStabilityTracker(require_declining=True)
        tracker.stability_classifier.incline_threshold = -0.2
        feed(tracker, EARLY)
        restored = SingleStabilityTracker.from_state(tracker.to_state())
        assert restored.require_declining is True
        assert restored.stability_classifier.incline_threshold == -0.2
        assert restored.classify().type == tracker.classify().type

    def test_state_without_the_keys_still_loads(self):
        """Snapshots written before the flag existed must keep working."""
        tracker = SingleStabilityTracker()
        feed(tracker, EARLY)
        state = tracker.to_state()
        del state["require_declining"], state["incline_threshold"]
        restored = SingleStabilityTracker.from_state(state)
        assert restored.require_declining is False
        assert restored.classify().type == "STABLE"

    def test_event_tracker_propagates_the_flag(self):
        event_tracker = EventStabilityTracker(require_declining=True)
        event_tracker.add_data({"var1": "a"})
        event_tracker.add_data({"var1": "b"})
        assert event_tracker.get_data()["var1"].require_declining is True

    def test_event_tracker_dump_load_preserves_the_flag(self):
        event_tracker = EventStabilityTracker(require_declining=True)
        event_tracker.add_data({"var1": "a"})
        event_tracker.add_data({"var1": "b"})
        restored = EventStabilityTracker.load(event_tracker.dump(), require_declining=True)
        assert restored.get_data()["var1"].require_declining is True


class TestRequireDecliningConfigWiring:
    def test_flag_reaches_per_variable_trackers(self):
        # CharsetDetector's `config` default is a shared mutable instance, so
        # pass explicit fresh configs (see test_time_dependent_stability.py).
        default = CharsetDetector(config=CharsetDetectorConfig())
        assert default.persistency.event_data_kwargs.get("require_declining") is None

        configured = CharsetDetector(config=CharsetDetectorConfig())
        configured.config.stability_require_declining = True
        rebuilt = CharsetDetector(config=configured.config.to_dict(method_id="CharsetDetector"))
        assert rebuilt.persistency.event_data_kwargs["require_declining"] is True

    def test_config_field_round_trips(self):
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.stability_require_declining = True
        restored = type(detector.config).from_dict(
            detector.config.to_dict(method_id="CharsetDetector"), "CharsetDetector"
        )
        assert restored.stability_require_declining is True

    def test_survives_auto_config(self):
        """set_configuration() rebuilds config from generate_detector_config,
        which emits none of the operator settings -- they get carried across."""
        detector = CharsetDetector(config=CharsetDetectorConfig(
            auto_config=True, stability_require_declining=True, use_static_vars=False,
        ))
        detector.set_configuration()
        assert detector.config.stability_require_declining is True
        assert detector.config.use_static_vars is False

    def test_does_not_pull_in_the_timestamp_requirement(self):
        """The flag is orthogonal to segmentation: no timestamps are asked
        for, and none are collected."""
        detector = CharsetDetector(config=CharsetDetectorConfig())
        detector.config.stability_require_declining = True
        rebuilt = CharsetDetector(config=detector.config.to_dict(method_id="CharsetDetector"))
        assert "segmentation" not in rebuilt.persistency.event_data_kwargs

        tracker = SingleStabilityTracker(require_declining=True)
        tracker.add_value("a", timestamp=1.0)
        assert tracker.timestamps == []
