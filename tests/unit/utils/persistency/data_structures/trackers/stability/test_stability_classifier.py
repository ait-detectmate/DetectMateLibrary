"""Tests for the stability tracking module.

This module tests StabilityClassifier, SingleVariableTracker,
MultiVariableTracker, and EventVariableTrackerData for variable
convergence and stability analysis.
"""

from detectmatelibrary.utils.persistency.data_structures.trackers import (
    StabilityClassifier,
    ClassificationMethods,
)
from detectmatelibrary.utils.persistency.data_structures.trackers.rle_list import RLEList


class TestStabilityClassifier:
    """Test suite for StabilityClassifier."""

    def test_initialization_default(self):
        """A bare classifier reads the block's default list."""
        classifier = StabilityClassifier()
        assert classifier.segment_threshs == [1.1, 0.3, 0.1, 0.01]
        assert classifier.n_segments == 4

    def test_initialization_custom_threshold(self):
        """Thresholds come in through the block, never a constructor arg."""
        classifier = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[0.8, 0.4, 0.2, 0.05])
        )
        assert classifier.segment_threshs == [0.8, 0.4, 0.2, 0.05]
        assert classifier.get_segment_thresholds() == [0.8, 0.4, 0.2, 0.05]

    def test_block_swap_re_derives_thresholds_and_count(self):
        """The property the (c, n) grid relies on: one ingest, many
        verdicts."""
        classifier = StabilityClassifier()
        classifier.classification = ClassificationMethods(segment_thresholds=[0.5, 0.5])
        assert classifier.segment_threshs == [0.5, 0.5]
        assert classifier.n_segments == 2
        classifier.classification = ClassificationMethods(segment_thresholds=[0.3] * 6)
        assert classifier.n_segments == 6

    def test_is_stable_with_rle_list_stable_pattern(self):
        """Test stability detection with RLEList - stable pattern."""
        classifier = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[1.1, 0.3, 0.1, 0.01])
        )

        # Create RLEList: 10 True, 5 False, 15 True (stabilizing to True)
        rle = RLEList()
        for _ in range(10):
            rle.append(True)
        for _ in range(5):
            rle.append(False)
        for _ in range(15):
            rle.append(True)

        result = classifier.is_stable(rle)
        assert isinstance(result, bool)

    def test_is_stable_with_rle_list_unstable_pattern(self):
        """Test stability detection with RLEList - unstable pattern."""
        classifier = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[1.1, 0.3, 0.1, 0.01])
        )

        # Create alternating pattern
        rle = RLEList()
        for _ in range(20):
            rle.append(True)
            rle.append(False)

        result = classifier.is_stable(rle)
        assert isinstance(result, bool)

    def test_is_stable_with_regular_list(self):
        """Test stability detection with regular list."""
        classifier = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[1.1, 0.3, 0.1, 0.01])
        )

        # Stable pattern
        stable_list = [1] * 10 + [0] * 5 + [1] * 15
        result = classifier.is_stable(stable_list)
        assert isinstance(result, bool)

    def test_different_segment_thresholds(self):
        """The same series is STABLE under a lenient list and UNSTABLE under a
        strict one."""
        # 4 segments of 10: means 1.0, 0.5, 0.0, 0.0
        series = [1] * 10 + [1, 0] * 5 + [0] * 20

        strict = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[1.1, 0.3, 0.1, 0.01])
        )
        lenient = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[1.1, 0.6, 0.1, 0.01])
        )

        assert strict.is_stable(series) is False   # 0.5 >= 0.3 in segment 2
        assert lenient.is_stable(series) is True   # 0.5 < 0.6


class TestStabilityClassifierMinSamples:
    """The fewest observations the enabled methods can be applied to."""

    def test_default_block_needs_one_observation_per_segment(self):
        assert StabilityClassifier().min_samples == 4

    def test_custom_list_needs_its_length(self):
        clf = StabilityClassifier(
            classification=ClassificationMethods(segment_thresholds=[0.5] * 7)
        )
        assert clf.min_samples == 7

    def test_time_only_block_still_cuts_segments(self):
        clf = StabilityClassifier(
            classification=ClassificationMethods(index=False, time=True, segment_thresholds=[0.5] * 3)
        )
        assert clf.min_samples == 3

    def test_slope_only_block_has_no_floor(self):
        """A threshold list the block never reads must not gate slope
        verdicts."""
        clf = StabilityClassifier(
            classification=ClassificationMethods(
                index=False, slope_index=True, segment_thresholds=[0.5] * 9
            )
        )
        assert clf.min_samples == 0

    def test_floor_follows_a_block_swap(self):
        clf = StabilityClassifier()
        clf.classification = ClassificationMethods(segment_thresholds=[0.5] * 8)
        assert clf.min_samples == 8
        clf.classification = ClassificationMethods(index=False, slope_time=True)
        assert clf.min_samples == 0
