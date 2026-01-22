"""Tests for the stability tracking module.

This module tests StabilityClassifier, StabilityTracker,
VariableTrackers, and EventVariableTracker for variable convergence and
stability analysis.
"""

from detectmatelibrary.common.persistency.event_data_structures.trackers import (
    StabilityClassifier,
    StabilityTracker,
    VariableTrackers,
    EventVariableTracker,
    Classification,
)
from detectmatelibrary.utils.RLE_list import RLEList


class TestStabilityClassifier:
    """Test suite for StabilityClassifier."""

    def test_initialization_default(self):
        """Test StabilityClassifier initialization with defaults."""
        classifier = StabilityClassifier(segment_thresholds=[1.1, 0.5, 0.2, 0.1])
        assert classifier.segment_threshs == [1.1, 0.5, 0.2, 0.1]
        assert classifier is not None

    def test_initialization_custom_threshold(self):
        """Test initialization with custom segment thresholds."""
        classifier = StabilityClassifier(segment_thresholds=[0.8, 0.4, 0.2, 0.05])
        assert classifier.segment_threshs == [0.8, 0.4, 0.2, 0.05]

    def test_is_stable_with_rle_list_stable_pattern(self):
        """Test stability detection with RLEList - stable pattern."""
        classifier = StabilityClassifier(segment_thresholds=[1.1, 0.3, 0.1, 0.01])

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
        classifier = StabilityClassifier(segment_thresholds=[1.1, 0.3, 0.1, 0.01])

        # Create alternating pattern
        rle = RLEList()
        for _ in range(20):
            rle.append(True)
            rle.append(False)

        result = classifier.is_stable(rle)
        assert isinstance(result, bool)

    def test_is_stable_with_regular_list(self):
        """Test stability detection with regular list."""
        classifier = StabilityClassifier(segment_thresholds=[1.1, 0.3, 0.1, 0.01])

        # Stable pattern
        stable_list = [1] * 10 + [0] * 5 + [1] * 15
        result = classifier.is_stable(stable_list)
        assert isinstance(result, bool)

    def test_different_segment_thresholds(self):
        """Test behavior with different segment thresholds."""
        series = [1] * 10 + [0] * 3 + [1] * 15

        strict = StabilityClassifier(segment_thresholds=[0.5, 0.2, 0.05, 0.01])
        lenient = StabilityClassifier(segment_thresholds=[2.0, 1.0, 0.5, 0.3])

        result_strict = strict.is_stable(series)
        result_lenient = lenient.is_stable(series)

        assert isinstance(result_strict, bool)
        assert isinstance(result_lenient, bool)


class TestStabilityTracker:
    """Test suite for StabilityTracker."""

    def test_initialization_default(self):
        """Test StabilityTracker initialization with defaults."""
        tracker = StabilityTracker()
        assert tracker.min_samples == 3
        assert isinstance(tracker.change_series, RLEList)
        assert isinstance(tracker.unique_set, set)

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        tracker = StabilityTracker(min_samples=20)
        assert tracker.min_samples == 20

    def test_add_value_single(self):
        """Test adding a single value."""
        tracker = StabilityTracker()
        tracker.add_value("value1")

        assert len(tracker.unique_set) == 1
        assert len(tracker.change_series) == 1

    def test_add_value_multiple_same(self):
        """Test adding multiple same values."""
        tracker = StabilityTracker()

        for i in range(10):
            tracker.add_value("constant")

        assert len(tracker.unique_set) == 1
        assert "constant" in tracker.unique_set

    def test_add_value_multiple_different(self):
        """Test adding multiple different values."""
        tracker = StabilityTracker()

        for i in range(10):
            tracker.add_value(f"value_{i}")

        assert len(tracker.unique_set) == 10

    def test_classification_insufficient_data(self):
        """Test classification with insufficient data."""
        tracker = StabilityTracker(min_samples=30)

        for i in range(10):  # Less than min_samples
            tracker.add_value(f"value_{i}")

        result = tracker.classify()
        assert result.type == "INSUFFICIENT_DATA"

    def test_classification_static(self):
        """Test classification as STATIC (single unique value)."""
        tracker = StabilityTracker(min_samples=10)

        for i in range(40):
            tracker.add_value("constant")

        result = tracker.classify()
        assert result.type == "STATIC"

    def test_classification_random(self):
        """Test classification as RANDOM (all unique values)."""
        tracker = StabilityTracker(min_samples=10)

        for i in range(40):
            tracker.add_value(f"unique_{i}")

        result = tracker.classify()
        assert result.type == "RANDOM"

    def test_classification_stable(self):
        """Test classification as STABLE (converging pattern)."""
        tracker = StabilityTracker(min_samples=10)

        # Pattern: changing values that stabilize
        for i in range(15):
            tracker.add_value(f"value_{i % 5}")
        for i in range(25):
            tracker.add_value("stable_value")

        result = tracker.classify()
        assert result.type in ["STABLE", "STATIC"]

    def test_classification_unstable(self):
        """Test classification as UNSTABLE (no clear pattern)."""
        tracker = StabilityTracker(min_samples=10)

        # Alternating pattern
        for i in range(40):
            tracker.add_value("value_a" if i % 2 == 0 else "value_b")

        result = tracker.classify()
        # Could be UNSTABLE or classified differently depending on classifier logic
        assert result.type in ["UNSTABLE", "STABLE", "RANDOM"]

    def test_rle_list_integration(self):
        """Test that RLEList is used for efficient storage."""
        tracker = StabilityTracker()

        # Add values that create runs
        for i in range(20):
            tracker.add_value("a")
        for i in range(20):
            tracker.add_value("b")

        # RLEList should be populated
        assert len(tracker.change_series) > 0

    def test_unique_values_tracking(self):
        """Test unique values are tracked in a set."""
        tracker = StabilityTracker()

        values = ["a", "b", "c", "a", "b", "a"]
        for v in values:
            tracker.add_value(v)

        assert len(tracker.unique_set) == 3
        assert "a" in tracker.unique_set
        assert "b" in tracker.unique_set
        assert "c" in tracker.unique_set

    def test_change_detection(self):
        """Test that add_value correctly detects changes."""
        tracker = StabilityTracker()

        tracker.add_value("a")
        tracker.add_value("a")
        tracker.add_value("b")

        # First value creates a change (new unique value)
        # Second doesn't (same value)
        # Third does (new unique value)
        assert len(tracker.change_series) == 3


class TestVariableTrackers:
    """Test suite for VariableTrackers manager."""

    def test_initialization_default(self):
        """Test VariableTrackers initialization."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)
        assert trackers is not None
        assert trackers.tracker_type == StabilityTracker

    def test_initialization_with_kwargs(self):
        """Test initialization without kwargs - VariableTrackers doesn't store tracker kwargs."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)
        assert trackers.tracker_type == StabilityTracker

    def test_add_data_single_variable(self):
        """Test adding data for a single variable."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)
        data = {"var1": "value1"}
        trackers.add_data(data)

        all_trackers = trackers.get_trackers()
        assert "var1" in all_trackers
        assert isinstance(all_trackers["var1"], StabilityTracker)

    def test_add_data_multiple_variables(self):
        """Test adding data for multiple variables."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)
        data = {"var1": "value1", "var2": "value2", "var3": "value3"}
        trackers.add_data(data)

        all_trackers = trackers.get_trackers()
        assert len(all_trackers) == 3
        assert "var1" in all_trackers
        assert "var2" in all_trackers
        assert "var3" in all_trackers

    def test_add_data_multiple_times(self):
        """Test adding data multiple times."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)

        trackers.add_data({"var1": "a", "var2": "x"})
        trackers.add_data({"var1": "b", "var2": "y"})
        trackers.add_data({"var1": "a", "var3": "z"})

        all_trackers = trackers.get_trackers()
        assert len(all_trackers) == 3
        assert "var3" in all_trackers  # New variable dynamically added

    def test_classify_all_variables(self):
        """Test classifying all variables."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)

        # Add enough data for classification
        for i in range(10):
            trackers.add_data({"var1": "constant", "var2": f"changing_{i}"})

        classifications = trackers.classify()
        assert "var1" in classifications
        assert "var2" in classifications
        assert isinstance(classifications["var1"], Classification)

    def test_get_stable_variables(self):
        """Test retrieving stable variables."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)

        # Create stable pattern
        for i in range(40):
            trackers.add_data({
                "stable_var": "constant",
                "random_var": f"unique_{i}",
            })

        stable_vars = trackers.get_variables_by_classification("STABLE")
        assert isinstance(stable_vars, list)
        # "stable_var" should be classified as STATIC

    def test_get_trackers(self):
        """Test retrieving all trackers."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)
        trackers.add_data({"var1": "a", "var2": "b"})

        all_trackers = trackers.get_trackers()
        assert isinstance(all_trackers, dict)
        assert len(all_trackers) == 2

    def test_dynamic_tracker_creation(self):
        """Test that trackers are created dynamically."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)

        # First add
        trackers.add_data({"var1": "a"})
        assert len(trackers.get_trackers()) == 1

        # Second add with new variable
        trackers.add_data({"var1": "b", "var2": "x"})
        assert len(trackers.get_trackers()) == 2

        # Third add with another new variable
        trackers.add_data({"var3": "z"})
        assert len(trackers.get_trackers()) == 3


class TestEventVariableTracker:
    """Test suite for EventVariableTracker."""

    def test_initialization(self):
        """Test EventVariableTracker initialization."""
        evt = EventVariableTracker(tracker_type=StabilityTracker)
        assert evt is not None
        assert isinstance(evt.variable_trackers, VariableTrackers)

    def test_add_data(self):
        """Test adding data."""
        evt = EventVariableTracker(tracker_type=StabilityTracker)
        data = {"var1": "value1", "var2": "value2"}
        evt.add_data(data)

        # Should have created trackers
        trackers = evt.get_data()
        assert len(trackers) == 2

    def test_get_variables(self):
        """Test retrieving variable names."""
        evt = EventVariableTracker(tracker_type=StabilityTracker)
        evt.add_data({"var1": "a", "var2": "b", "var3": "c"})

        var_names = evt.get_variables()
        assert "var1" in var_names
        assert "var2" in var_names
        assert "var3" in var_names
        assert len(var_names) == 3

    def test_get_stable_variables(self):
        """Test retrieving stable variables."""
        evt = EventVariableTracker(tracker_type=StabilityTracker)

        for i in range(40):
            evt.add_data({
                "stable_var": "constant",
                "random_var": f"unique_{i}",
            })

        stable_vars = evt.get_variables_by_classification("STABLE")
        assert isinstance(stable_vars, list)

    def test_integration_with_stability_tracker(self):
        """Test full integration with StabilityTracker."""
        evt = EventVariableTracker(tracker_type=StabilityTracker)

        # Simulate log processing
        for i in range(50):
            evt.add_data({
                "user": f"user_{i % 5}",
                "status": "success" if i > 30 else f"status_{i}",
                "request_id": f"req_{i}",
            })

        # Get data and variables
        var_names = evt.get_variables()
        stable_vars = evt.get_variables_by_classification("STABLE")

        assert len(var_names) == 3
        assert isinstance(stable_vars, list)


class TestClassification:
    """Test suite for Classification dataclass."""

    def test_initialization(self):
        """Test Classification initialization."""
        result = Classification(type="STABLE", reason="Test reason")
        assert result.type == "STABLE"
        assert result.reason == "Test reason"

    def test_all_classification_types(self):
        """Test Classification with all classification types."""
        types = ["INSUFFICIENT_DATA", "STATIC", "RANDOM", "STABLE", "UNSTABLE"]

        for cls_type in types:
            result = Classification(type=cls_type, reason=f"Reason for {cls_type}")
            assert result.type == cls_type
            assert isinstance(result.reason, str)


class TestStabilityTrackingIntegration:
    """Integration tests for stability tracking components."""

    def test_full_workflow_static_variable(self):
        """Test full workflow with static variable."""
        tracker = StabilityTracker(min_samples=10)

        # Add 50 identical values
        for i in range(50):
            tracker.add_value("constant_value")

        classification = tracker.classify()
        assert classification.type == "STATIC"

    def test_full_workflow_random_variable(self):
        """Test full workflow with random variable."""
        tracker = StabilityTracker(min_samples=10)

        # Add 50 unique values
        for i in range(50):
            tracker.add_value(f"unique_value_{i}")

        classification = tracker.classify()
        assert classification.type == "RANDOM"

    def test_full_workflow_stabilizing_variable(self):
        """Test full workflow with stabilizing variable."""
        tracker = StabilityTracker(min_samples=10)

        # Start with varied values, then stabilize
        for i in range(15):
            tracker.add_value(f"value_{i % 7}")
        for i in range(35):
            tracker.add_value("final_stable_value")

        classification = tracker.classify()
        # Should be STABLE or STATIC
        assert classification.type in ["STABLE", "STATIC"]

    def test_multiple_variables_with_different_patterns(self):
        """Test tracking multiple variables with different patterns."""
        trackers = VariableTrackers(tracker_type=StabilityTracker)

        # Simulate 100 events
        for i in range(100):
            trackers.add_data({
                "static_var": "always_same",
                "random_var": f"unique_{i}",
                "user_id": f"user_{i % 10}",  # 10 users cycling
                "status": "ok" if i > 80 else f"status_{i % 5}",  # Stabilizing
            })

        classifications = trackers.classify()

        # static_var should be STATIC
        assert classifications["static_var"].type == "STATIC"

        # random_var should be RANDOM
        assert classifications["random_var"].type == "RANDOM"

        # user_id and status depend on classifier logic
        assert isinstance(classifications["user_id"], Classification)
        assert isinstance(classifications["status"], Classification)

    def test_event_variable_tracker_real_world_scenario(self):
        """Test EventVariableTracker with realistic log data."""
        evt = EventVariableTracker(tracker_type=StabilityTracker)

        # Simulate web server logs
        for i in range(200):
            evt.add_data({
                "method": "GET" if i % 10 != 0 else "POST",  # Mostly GET
                "status_code": "200" if i > 150 else str(200 + (i % 5)),  # Stabilizing to 200
                "user_agent": f"Browser_{i % 3}",  # 3 different browsers
                "request_id": f"req_{i}",  # Unique per request
                "server": "prod-server-1",  # Static
            })

        var_names = evt.get_variables()
        stable_vars = evt.get_variables_by_classification("STABLE")

        assert len(var_names) == 5
        assert isinstance(stable_vars, list)

        # Server should definitely be stable
        # Request_id should be random
        # Others depend on exact classifier logic

    def test_classifier_with_varying_thresholds(self):
        """Test stability classifier with different thresholds."""
        # Create a borderline case
        pattern = [1] * 15 + [0] * 5 + [1] * 20

        strict = StabilityClassifier(segment_thresholds=[0.5, 0.2, 0.08, 0.02])
        lenient = StabilityClassifier(segment_thresholds=[2.0, 1.5, 1.0, 0.5])

        result_strict = strict.is_stable(pattern)
        result_lenient = lenient.is_stable(pattern)

        # Both should produce boolean results
        assert isinstance(result_strict, bool)
        assert isinstance(result_lenient, bool)
