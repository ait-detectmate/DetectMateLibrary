"""Tracks whether a variable is converging to a constant value."""

from typing import Any, Set

from detectmatelibrary.utils.preview_helpers import list_preview_str
from detectmatelibrary.utils.RLE_list import RLEList

from ..classifiers.stability_classifier import StabilityClassifier
from .base import SingleTracker, Classification


class StabilityTracker(SingleTracker):
    """Tracks whether a single variable is converging to a constant value."""

    def __init__(self, min_samples: int = 3) -> None:
        self.min_samples = min_samples
        self.change_series: RLEList[bool] = RLEList()
        self.unique_set: Set[Any] = set()
        self.stability_classifier: StabilityClassifier = StabilityClassifier(
            segment_thresholds=[1.1, 0.3, 0.1, 0.01],
        )

    def add_value(self, value: Any) -> None:
        """Add a new value to the tracker."""
        unique_set_size_before = len(self.unique_set)
        self.unique_set.add(value)
        has_changed = len(self.unique_set) - unique_set_size_before > 0
        self.change_series.append(has_changed)

    def classify(self) -> Classification:
        """Classify the variable."""
        if len(self.change_series) < self.min_samples:
            return Classification(
                type="INSUFFICIENT_DATA",
                reason=f"Not enough data (have {len(self.change_series)}, need {self.min_samples})"
            )
        elif len(self.unique_set) == 1:
            return Classification(
                type="STATIC",
                reason="Unique set size is 1"
            )
        elif len(self.unique_set) == len(self.change_series):
            return Classification(
                type="RANDOM",
                reason=f"Unique set size equals number of samples ({len(self.change_series)})"
            )
        elif self.stability_classifier.is_stable(self.change_series):
            return Classification(
                type="STABLE",
                reason=(
                    f"Segment means of change series {self.stability_classifier.get_last_segment_means()} "
                    f"are below segment thresholds: {self.stability_classifier.get_segment_thresholds()}"
                )
            )
        else:
            return Classification(
                type="UNSTABLE",
                reason="No classification matched; variable is unstable"
            )

    def __repr__(self) -> str:
        # show only part of the series for brevity
        series_str = list_preview_str(self.change_series)
        unique_set_str = "{" + ", ".join(map(str, list_preview_str(self.unique_set))) + "}"
        RLE_str = list_preview_str(self.change_series.runs())
        return (
            f"{self.__class__.__name__}(classification={self.classify()}, change_series={series_str}, "
            f"unique_set={unique_set_str}, RLE={RLE_str})"
        )
