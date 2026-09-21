from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
    ClassificationMethods,
    _classification_from_state,
)


class TestSingleStabilityTrackerExpandValue:
    def test_default_add_value(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        tracker.add_value("world")
        assert tracker.unique_set == {"hello", "world"}

    def test_custom_add_value(self):
        tracker = SingleStabilityTracker(add_value_fn="CharsetDetector")
        tracker.add_value("hello")
        tracker.add_value("world")
        assert tracker.unique_set == {"h", "e", "l", "o", "w", "r", "d"}

    def test_expand_value_change_series_tracks_growth(self):
        tracker = SingleStabilityTracker(add_value_fn="CharsetDetector")
        tracker.add_value("ab")           # adds {a, b}, change=True
        tracker.add_value("ba")           # adds nothing new, change=False
        tracker.add_value("c")            # adds {c}, change=True
        assert list(tracker.change_series) == [True, False, True]

    def test_expand_value_round_trip(self):
        tracker = SingleStabilityTracker(add_value_fn="CharsetDetector")
        tracker.add_value("hello")
        tracker.add_value("world")
        state = tracker.to_state()
        restored = SingleStabilityTracker.from_state(state)
        assert restored.add_value_fn == "CharsetDetector"
        assert restored.unique_set == {"h", "e", "l", "o", "w", "r", "d"}
        # subsequent ingestion still unions characters
        restored.add_value("xy")
        assert {"x", "y"} <= restored.unique_set

    def test_legacy_state_without_expand_value_defaults_false(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        restored = SingleStabilityTracker.from_state(state)
        assert restored.add_value_fn == "default"
        assert restored.unique_set == {"hello"}


class TestEventStabilityTrackerExpandValue:
    def test_default_event_tracker_uses_add_semantics(self):
        event_tracker = EventStabilityTracker()
        event_tracker.add_data({"var1": "hello"})
        single = event_tracker.get_data()["var1"]
        assert single.add_value_fn == "default"
        assert single.detector_config is None
        assert single.unique_set == {"hello"}

    def test_expand_value_propagates_to_per_variable_trackers(self):
        event_tracker = EventStabilityTracker(add_value_fn="CharsetDetector")
        event_tracker.add_data({"var1": "hello"})
        event_tracker.add_data({"var1": "world"})
        single = event_tracker.get_data()["var1"]
        assert single.add_value_fn == "CharsetDetector"
        assert single.detector_config is None
        assert single.unique_set == {"h", "e", "l", "o", "w", "r", "d"}

    def test_each_new_variable_gets_its_own_configured_tracker(self):
        event_tracker = EventStabilityTracker(add_value_fn="CharsetDetector")
        event_tracker.add_data({"a": "ab", "b": "cd"})
        a = event_tracker.get_data()["a"]
        b = event_tracker.get_data()["b"]
        assert a.add_value_fn == "CharsetDetector"
        assert b.add_value_fn == "CharsetDetector"
        assert a.detector_config is None
        assert b.detector_config is None
        assert a.unique_set == {"a", "b"}
        assert b.unique_set == {"c", "d"}

    def test_post_load_new_variable_honors_expand_value(self):
        """After dump/load, a variable that wasn't present at save time should
        still use expand_value semantics when first ingested."""
        original = EventStabilityTracker(add_value_fn="CharsetDetector")
        original.add_data({"known": "abc"})
        blob = original.dump()
        restored = EventStabilityTracker.load(blob, add_value_fn="CharsetDetector")

        # Ingest a brand-new variable not present in the saved state
        restored.add_data({"known": "de", "newvar": "xy"})

        new_tracker = restored.get_data()["newvar"]
        assert new_tracker.add_value_fn == "CharsetDetector"
        assert new_tracker.detector_config is None
        assert new_tracker.unique_set == {"x", "y"}

        # And the existing variable continues to expand correctly
        known_tracker = restored.get_data()["known"]
        assert known_tracker.add_value_fn == "CharsetDetector"
        assert known_tracker.detector_config is None
        assert {"a", "b", "c", "d", "e"} <= known_tracker.unique_set


class TestSingleStabilityTrackerExtraState:
    def test_extra_state_defaults_to_empty_dict(self):
        tracker = SingleStabilityTracker()
        assert tracker.extra_state == {}

    def test_extra_state_round_trip(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        tracker.extra_state["freq"] = {"a": {"b": 3, "c": 1}}
        tracker.extra_state["total_freq"] = {"a": 4}
        state = tracker.to_state()
        restored = SingleStabilityTracker.from_state(state)
        assert restored.extra_state == {
            "freq": {"a": {"b": 3, "c": 1}},
            "total_freq": {"a": 4},
        }

    def test_legacy_state_without_extra_state_defaults_empty(self):
        tracker = SingleStabilityTracker()
        tracker.add_value("hello")
        state = tracker.to_state()
        state.pop("extra_state", None)  # simulate pre-flag snapshot
        restored = SingleStabilityTracker.from_state(state)
        assert restored.extra_state == {}

    def test_extra_state_round_trip_through_msgpack(self):
        event_tracker = EventStabilityTracker()
        event_tracker.add_data({"var1": "abc"})
        single = event_tracker.get_data()["var1"]
        single.extra_state["freq"] = {-1: {"a": 2}, "a": {"b": 1}}
        single.extra_state["total_freq"] = {-1: 2, "a": 1}

        blob = event_tracker.dump()
        restored = EventStabilityTracker.load(blob)
        r_single = restored.get_data()["var1"]
        assert r_single.extra_state["freq"] == {-1: {"a": 2}, "a": {"b": 1}}
        assert r_single.extra_state["total_freq"] == {-1: 2, "a": 1}


class TestSegmentThresholdsOnTheTracker:
    """The threshold list lives in the block and only there."""

    def test_default_tracker_uses_the_historical_list(self):
        tracker = SingleStabilityTracker()
        assert tracker.stability_classifier.segment_threshs == [1.1, 0.3, 0.1, 0.01]
        assert tracker.stability_classifier.n_segments == 4

    def test_constructor_copies_the_block_deeply(self):
        """An EventStabilityTracker shares one block across every variable
        tracker it builds; a shallow copy would leave the list shared."""
        block = ClassificationMethods(segment_thresholds=[0.5, 0.4])
        tracker = SingleStabilityTracker(classification=block)
        block.segment_thresholds.append(0.3)
        assert tracker.classification.segment_thresholds == [0.5, 0.4]
        assert tracker.stability_classifier.n_segments == 2

    def test_setter_copies_the_block_deeply_too(self):
        block = ClassificationMethods(segment_thresholds=[0.5, 0.4])
        tracker = SingleStabilityTracker()
        tracker.classification = block
        block.segment_thresholds[0] = 9.9
        assert tracker.classification.segment_thresholds == [0.5, 0.4]

    def test_block_swap_re_derives_count_and_reason(self):
        """One ingest, several verdicts: the grid's whole premise."""
        tracker = SingleStabilityTracker()
        for i in range(24):
            tracker.add_value(f"v{i % 5}")  # 5 values cycling -> not STATIC, not RANDOM
        tracker.classification = ClassificationMethods(segment_thresholds=[0.9, 0.9])
        assert tracker.stability_classifier.n_segments == 2
        assert "[0.9, 0.9]" in tracker.classify().reason
        tracker.classification = ClassificationMethods(segment_thresholds=[0.9] * 6)
        assert tracker.stability_classifier.n_segments == 6
        assert "[0.9, 0.9, 0.9, 0.9, 0.9, 0.9]" in tracker.classify().reason


class TestSegmentThresholdsState:
    """to_state() carries the list inside the block; from_state() reads it from
    wherever an older library version put it."""

    @staticmethod
    def _ingested(**kwargs) -> SingleStabilityTracker:
        tracker = SingleStabilityTracker(**kwargs)
        for v in ["a", "b", "a", "c", "a"]:
            tracker.add_value(v)
        return tracker

    def test_to_state_has_no_top_level_key(self):
        state = self._ingested(
            classification=ClassificationMethods(segment_thresholds=[0.5, 0.2])
        ).to_state()
        assert "segment_thresholds" not in state
        assert state["classification"]["segment_thresholds"] == [0.5, 0.2]

    def test_from_state_restores_the_list_from_the_block(self):
        original = self._ingested(
            classification=ClassificationMethods(segment_thresholds=[0.5, 0.2])
        )
        restored = SingleStabilityTracker.from_state(original.to_state())
        assert restored.classification == original.classification
        assert restored.stability_classifier.segment_threshs == [0.5, 0.2]

    def test_block_list_wins_over_a_top_level_key(self):
        """First row of the migration table: a block with the field is taken
        as-is, whatever else the state carries."""
        state = self._ingested().to_state()
        state["classification"]["segment_thresholds"] = [0.7, 0.6]
        state["segment_thresholds"] = [0.1, 0.1, 0.1]
        assert _classification_from_state(state).segment_thresholds == [0.7, 0.6]

    def test_0_5_3_state_merges_the_top_level_list_into_the_block(self):
        """Second row: the four-method split (0.5.3) wrote the block without
        the field and the list at top level."""
        state = self._ingested(
            classification=ClassificationMethods(index=True, time=True, decision="majority")
        ).to_state()
        del state["classification"]["segment_thresholds"]
        state["segment_thresholds"] = [0.8, 0.4, 0.2]
        restored = SingleStabilityTracker.from_state(state)
        assert restored.classification.enabled == ("index", "time")
        assert restored.classification.decision == "majority"
        assert restored.stability_classifier.segment_threshs == [0.8, 0.4, 0.2]
        assert restored.stability_classifier.n_segments == 3

    def test_block_without_field_and_no_top_level_key_gets_the_default(self):
        """Third row: never written, tolerated."""
        state = self._ingested().to_state()
        del state["classification"]["segment_thresholds"]
        state.pop("segment_thresholds", None)
        restored = SingleStabilityTracker.from_state(state)
        assert restored.stability_classifier.segment_threshs == [1.1, 0.3, 0.1, 0.01]

    def test_pre_four_method_state_keeps_its_top_level_list(self):
        """Fourth row: legacy segmentation / require_declining /
        incline_threshold plus the top-level list."""
        state = self._ingested().to_state()
        del state["classification"]
        state.update(
            segmentation="both",
            require_declining=True,
            incline_threshold=-0.2,
            segment_thresholds=[0.9, 0.5],
        )
        restored = SingleStabilityTracker.from_state(state)
        assert restored.classification.enabled == ("index", "time", "slope_index")
        assert restored.classification.slope_threshold == -0.2
        assert restored.classification.decision == "consensus"
        assert restored.stability_classifier.segment_threshs == [0.9, 0.5]

    def test_pre_four_method_state_without_a_list_gets_the_default(self):
        """Fifth row: never written, tolerated."""
        state = self._ingested().to_state()
        del state["classification"]
        state.pop("segment_thresholds", None)
        state["segmentation"] = "time"
        restored = SingleStabilityTracker.from_state(state)
        assert restored.classification.enabled == ("time",)
        assert restored.stability_classifier.segment_threshs == [1.1, 0.3, 0.1, 0.01]


class TestSegmentFloor:
    """A series shorter than the segment count is INSUFFICIENT_DATA rather than
    scored over empty segments.

    One test per cell of the spec's §7 table; L = series length, n =
    segment count, m = the tracker's min_samples.
    """

    @staticmethod
    def _fed(tracker: SingleStabilityTracker, values) -> SingleStabilityTracker:
        for v in values:
            tracker.add_value(v)
        return tracker

    def test_three_of_two_values_under_four_segments_is_insufficient(self):
        """At defaults (m=3, n=4, L=3): today's one behaviour change."""
        verdict = self._fed(SingleStabilityTracker(), ["a", "b", "a"]).classify()
        assert verdict.type == "INSUFFICIENT_DATA"
        assert verdict.reason == "Not enough data for 4 segments (have 3, need 4)"

    def test_four_observations_clear_the_default_floor(self):
        verdict = self._fed(SingleStabilityTracker(), ["a", "b", "a", "a"]).classify()
        assert verdict.type in ("STABLE", "UNSTABLE")

    def test_static_keeps_the_tracker_floor(self):
        """With m <= L < n and one unique value, STATIC is decided before
        segments."""
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(segment_thresholds=[0.5] * 10)
        )
        assert self._fed(tracker, ["a", "a", "a"]).classify().type == "STATIC"

    def test_random_keeps_the_tracker_floor(self):
        """With m <= L < n and every value unique, RANDOM is decided before
        segments."""
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(segment_thresholds=[0.5] * 10)
        )
        assert self._fed(tracker, ["a", "b", "c"]).classify().type == "RANDOM"

    def test_slope_only_block_has_no_segment_floor(self):
        """With m <= L < n and no segment method, the list is never read, so it
        must not gate the verdict."""
        tracker = SingleStabilityTracker(
            classification=ClassificationMethods(
                index=False, slope_index=True, segment_thresholds=[0.5] * 10
            )
        )
        assert self._fed(tracker, ["a", "b", "a"]).classify().type in ("STABLE", "UNSTABLE")

    def test_the_larger_floor_governs(self):
        """When m=10 > n=4 and L=9, step 1 fires with its own reason."""
        tracker = SingleStabilityTracker(min_samples=10)
        verdict = self._fed(tracker, ["a", "b", "a", "b", "a", "b", "a", "b", "a"]).classify()
        assert verdict.type == "INSUFFICIENT_DATA"
        assert verdict.reason == "Not enough data (have 9, need 10)"

    def test_floor_follows_a_block_swap(self):
        """Five observations: verdict under four segments, INSUFFICIENT_DATA
        under eight, verdict again after swapping back."""
        tracker = self._fed(SingleStabilityTracker(), ["a", "b", "a", "b", "a"])
        assert tracker.classify().type in ("STABLE", "UNSTABLE")
        tracker.classification = ClassificationMethods(segment_thresholds=[0.5] * 8)
        verdict = tracker.classify()
        assert verdict.type == "INSUFFICIENT_DATA"
        assert verdict.reason == "Not enough data for 8 segments (have 5, need 8)"
        tracker.classification = ClassificationMethods()
        assert tracker.classify().type in ("STABLE", "UNSTABLE")
