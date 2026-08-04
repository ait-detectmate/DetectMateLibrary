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
        non-decreasing, non-zero span), boundaries are equal-DURATION
        cuts of the observed time span, mapped back to indices. Falls
        back to equal-count on missing / mismatched / non-finite / out-
        of-order timestamps and on zero span. A duration cut that leaves
        a segment empty is kept as-is: nothing observed in that window
        means no changes in it, which ``is_stable`` scores as a mean of
        0.0.
        """
        segment_size = total_len / self.n_segments
        count_boundaries = [int(i * segment_size) for i in range(self.n_segments + 1)]
        count_boundaries[-1] = total_len
        try:
            use_time = (
                timestamps is not None
                and len(timestamps) == total_len
                and total_len > 0
                and bool(np.all(np.isfinite(timestamps)))
                # np.searchsorted below requires sorted input. Merged sources or
                # concurrent writers can deliver stamps out of order, which would
                # silently produce wrong boundaries rather than an error. O(N),
                # same cost as the isfinite scan above.
                and bool(np.all(np.diff(timestamps) >= 0))
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
        return count_boundaries

    def is_stable(
        self,
        change_series: RLEList[bool] | List[bool],
        timestamps: List[float] | None = None,
    ) -> bool:
        """Determine if a list of segment means is stable.

        Works efficiently with RLEList without expanding to a full list.
        When timestamps are given (one per occurrence, non-decreasing),
        segments are equal-duration cuts of the time span instead of
        equal-count cuts of the series. See ``_segment_boundaries`` for
        the conditions under which time mode falls back to count mode.

        A segment with no observations in it scores a mean of 0.0 -- no
        occurrences means no changes. Equal-duration cuts of a bursty
        series leave such segments routinely; pair ``time`` with
        ``count`` (segmentation ``both``) if that leniency matters.
        """
        total_len = len(change_series)
        if total_len == 0:
            return True

        segment_boundaries = self._segment_boundaries(total_len, timestamps)

        if isinstance(change_series, RLEList):
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

            self.segment_means = [
                segment_sums[i] / segment_counts[i] if segment_counts[i] > 0 else 0.0
                for i in range(self.n_segments)
            ]
        else:
            self.segment_means = [
                float(np.mean(change_series[segment_boundaries[i]:segment_boundaries[i + 1]]))
                if segment_boundaries[i + 1] > segment_boundaries[i] else 0.0
                for i in range(self.n_segments)
            ]
        return all([not q >= thresh for q, thresh in zip(self.segment_means, self.segment_threshs)])

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
