"""Classifier for stability based on segment means."""

from typing import List
import numpy as np

from detectmatelibrary.utils.RLE_list import RLEList


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
