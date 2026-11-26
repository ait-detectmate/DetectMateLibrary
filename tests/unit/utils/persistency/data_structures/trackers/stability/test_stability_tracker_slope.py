"""Tests for the slope classification methods on the stability trackers."""
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    SingleStabilityTracker,
    EventStabilityTracker,
    ClassificationMethods,
)
from tests.support.stability import DENSE_EARLY, EARLY, LATE_BUT_PASSING, feed


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
        """STATIC / RANDOM, and INSUFFICIENT_DATA below the tracker's own
        min_samples, are decided before any method is consulted, so no method
        setting can reach them.

        (A segment method adds a second INSUFFICIENT_DATA floor at the
        segment count, after STATIC and RANDOM; that one does read the
        block.)
        """
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
            "index", "time", "segment_thresholds", "slope_index", "slope_time",
            "slope_threshold", "decision",
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
