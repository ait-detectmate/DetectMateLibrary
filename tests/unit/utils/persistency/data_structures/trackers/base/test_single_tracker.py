"""Tests for detectmatelibrary.utils.persistency.data_structures.trackers.base.

single_tracker.
"""
from detectmatelibrary.utils.persistency.data_structures.trackers import Classification


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
