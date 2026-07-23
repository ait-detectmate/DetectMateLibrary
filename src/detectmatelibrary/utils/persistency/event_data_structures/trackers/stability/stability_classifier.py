"""Classifier for stability based on segment means."""

from typing import List
import numpy as np

from detectmatelibrary.utils.persistency.rle_list import RLEList


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

    def _segment_boundaries(self, total_len: int, timestamps: List[float] | None = None) -> List[int]:
        """Index boundaries of n_segments segments over total_len items.

        Equal-count by default. When timestamps are given (one per item,
        chronological, non-zero span), boundaries are equal-DURATION
        cuts of the observed time span, mapped back to indices. Falls
        back to equal-count on missing/mismatched/non-finite timestamps
        or zero span.
        """
        try:
            use_time = (
                timestamps is not None
                and len(timestamps) == total_len
                and total_len > 0
                and bool(np.all(np.isfinite(timestamps)))
                and timestamps[-1] > timestamps[0]
            )
        except TypeError:
            # e.g. a None entry: not comparable/convertible -> equal-count
            use_time = False
        if use_time and timestamps is not None:  # 2nd clause narrows for mypy
            t_first, t_last = timestamps[0], timestamps[-1]
            cuts = [
                t_first + k * (t_last - t_first) / self.n_segments
                for k in range(self.n_segments + 1)
            ]
            boundaries = [int(np.searchsorted(timestamps, t, side="left")) for t in cuts]
            boundaries[0] = 0
            boundaries[-1] = total_len
            return boundaries
        segment_size = total_len / self.n_segments
        boundaries = [int(i * segment_size) for i in range(self.n_segments + 1)]
        boundaries[-1] = total_len
        return boundaries

    def is_stable(
        self,
        change_series: RLEList[bool] | List[bool],
        timestamps: List[float] | None = None,
    ) -> bool:
        """Determine if a list of segment means is stable.

        Works efficiently with RLEList without expanding to a full list.
        When timestamps are given (one per occurrence, chronological),
        segments are equal-duration cuts of the time span instead of
        equal-count cuts of the series.
        """
        # Handle both RLEList and regular list
        if isinstance(change_series, RLEList):
            total_len = len(change_series)
            if total_len == 0:
                return True

            segment_boundaries = self._segment_boundaries(total_len, timestamps)

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
            if timestamps is not None and len(timestamps) == len(change_series):
                b = self._segment_boundaries(len(change_series), timestamps)
                self.segment_means = [
                    float(np.mean(change_series[b[i]:b[i + 1]])) if b[i + 1] > b[i] else np.nan
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

    def __call__(
        self, change_series: RLEList[bool] | List[bool], timestamps: List[float] | None = None
    ) -> bool:
        return self.is_stable(change_series, timestamps=timestamps)

    def __repr__(self) -> str:
        return (
            f"StabilityClassifier(segment_threshs={self.segment_threshs}, "
            f"segment_means={self.segment_means})"
        )
