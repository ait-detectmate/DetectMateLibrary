# A tracker is a data structure that stores a specific feature of a variable
# and tracks the behavior of that feature over time/events.
# It operates within the persistency framework to monitor how variables evolve.
# It is interchangable with other EventDataStructure implementations.

# from src.detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode
from typing import Any, Dict, Set, Type, List
from dataclasses import dataclass
import numpy as np

from detectmatelibrary.utils.preview_helpers import list_preview_str, format_dict_repr
from detectmatelibrary.utils.RLE_list import RLEList

from .base import EventDataStructure


class StabilityClassifier:
    """Classifier for stability based on segment means."""
    def __init__(self, segment_thresholds: List[float], min_samples: int = 10):
        self.segment_threshs = segment_thresholds
        self.min_samples = min_samples
        # for RLELists
        self.segment_sums = [0.0] * len(segment_thresholds)
        self.segment_counts = [0] * len(segment_thresholds)
        self.n_segments = len(self.segment_threshs)
        # for lists
        self.segment_means: List[float] = []

    def is_stable(self, change_series: RLEList[bool] | List[bool]) -> bool:
        """Determine if a list of segment means is stable.

        Works efficiently with RLEList without expanding to a full list.
        """
        # Handle both RLEList and regular list
        if isinstance(change_series, RLEList):
            total_len = len(change_series)
            if total_len == 0:
                return True

            # Calculate segment boundaries
            segment_size = total_len / self.n_segments
            segment_boundaries = [int(i * segment_size) for i in range(self.n_segments + 1)]
            segment_boundaries[-1] = total_len

            # Compute segment means directly from RLE runs
            segment_sums = [0.0] * self.n_segments
            segment_counts = [0] * self.n_segments

            position = 0
            for value, count in change_series.runs():
                run_start = position
                run_end = position + count

                # Find which segments this run overlaps with
                for seg_idx in range(self.n_segments):
                    seg_start = segment_boundaries[seg_idx]
                    seg_end = segment_boundaries[seg_idx + 1]

                    # Calculate overlap between run and segment
                    overlap_start = max(run_start, seg_start)
                    overlap_end = min(run_end, seg_end)
                    overlap_count = max(0, overlap_end - overlap_start)

                    if overlap_count > 0:
                        segment_sums[seg_idx] += value * overlap_count
                        segment_counts[seg_idx] += overlap_count

                position = run_end

            # Calculate means
            self.segment_means = [
                segment_sums[i] / segment_counts[i] if segment_counts[i] > 0 else np.nan
                for i in range(self.n_segments)
            ]
        else:
            # Original implementation for regular lists
            self.segment_means = self._compute_segment_means(change_series)
        return all([not q >= thresh for q, thresh in zip(self.segment_means, self.segment_threshs)])

    def _compute_segment_means(self, change_series: List[bool]) -> List[float]:
        """Get means of each segment for a normal list."""
        segments = np.array_split(change_series, self.n_segments)
        return list(map(lambda x: np.mean(x) if len(x) > 0 else np.nan, segments))

    def get_last_segment_means(self) -> List[float]:
        return self.segment_means

    def get_segment_thresholds(self) -> List[float]:
        return self.segment_threshs

    def __call__(self, change_series: RLEList[bool] | List[bool]) -> bool:
        return self.is_stable(change_series)

    def __repr__(self) -> str:
        return (
            f"StabilityClassifier(segment_threshs={self.segment_threshs}, "
            f"segment_means={self.segment_means})"
        )


@dataclass
class Classification:
    type: str = ""
    reason: str = ""


class StabilityTracker:
    """Tracks whether a variable is converging to a constant value."""

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
            f"StabilityTracker(classification={self.classify()}, series={series_str}, "
            f"unique_set={unique_set_str}, RLE={RLE_str})"
        )


class VariableTrackers:
    """Tracks multiple variables using individual trackers."""

    def __init__(self, tracker_type: Type[StabilityTracker] = StabilityTracker) -> None:
        self.trackers: Dict[str, StabilityTracker] = {}
        self.tracker_type: Type[StabilityTracker] = tracker_type

    def add_data(self, data_object: Dict[str, Any]) -> None:
        """Add data to the appropriate variable trackers."""
        for var_name, value in data_object.items():
            if var_name not in self.trackers:
                self.trackers[var_name] = self.tracker_type()
            self.trackers[var_name].add_value(value)

    def get_trackers(self) -> Dict[str, StabilityTracker]:
        """Get the current variable trackers."""
        return self.trackers

    def classify(self) -> Dict[str, Any]:
        """Classify all tracked variables."""
        classifications = {}
        for var_name, tracker in self.trackers.items():
            classifications[var_name] = tracker.classify()
        return classifications

    def __repr__(self) -> str:
        strs = format_dict_repr(self.trackers, indent="\t")
        return f"VariableTrackers{{\n\t{strs}\n}}\n"


class EventVariableTracker(EventDataStructure):
    """Event data structure that tracks variable behaviors over time (or rather
    events)."""

    def __init__(self, tracker_type: Type[StabilityTracker] = StabilityTracker) -> None:
        self.variable_trackers = VariableTrackers(tracker_type=tracker_type)
        self.current_data = None

    def add_data(self, data_object: Any) -> None:
        """Add data to the variable trackers."""
        self.variable_trackers.add_data(data_object)

    def get_data(self) -> Any:
        """Retrieve the tracker's stored data."""
        return self.variable_trackers.get_trackers()

    def get_variables(self) -> list[str]:
        """Get the list of tracked variable names."""
        return list(self.variable_trackers.get_trackers().keys())

    @staticmethod
    def to_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw data into the format expected by the tracker."""
        return raw_data

    def __repr__(self) -> str:
        strs = format_dict_repr(self.variable_trackers.get_trackers(), indent="\t")
        return f"EventVariableTracker(data={{\n\t{strs}\n}}"
