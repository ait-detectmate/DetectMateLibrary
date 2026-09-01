"""Classifier for stability based on segment means."""

from typing import Dict, List
import numpy as np

from detectmatelibrary.utils.persistency.rle_list import RLEList
from .classification_methods import ClassificationMethods


def _timestamps_usable(timestamps: List[float] | None, total_len: int) -> bool:
    """Whether these timestamps can carry a time-axis computation.

    Shared by ``_segment_boundaries`` (the ``time`` method) and ``slope()``
    (the ``slope_time`` method), so both fall back to the index axis under
    exactly the same conditions. ``_slope`` still degrades further on its
    own: even when this predicate says yes, it drops to the index axis when
    the first observation's offset leaves no usable span (see its
    ``u_first >= 1.0`` guard) -- a case ``_segment_boundaries`` has no
    equivalent for.

    ``np.searchsorted`` and the centroid both require sorted input. Merged
    sources or concurrent writers can deliver stamps out of order, which
    would silently produce wrong boundaries rather than an error. O(N), the
    same cost as the isfinite scan.
    """
    try:
        return (
            timestamps is not None
            and len(timestamps) == total_len
            and total_len > 0
            and bool(np.all(np.isfinite(timestamps)))
            and bool(np.all(np.diff(timestamps) >= 0))
            and timestamps[-1] > timestamps[0]
        )
    except TypeError:
        # e.g. a None entry: not comparable/convertible -> index axis
        return False


class StabilityClassifier:
    """Classifier for stability based on segment means."""
    def __init__(
        self,
        segment_thresholds: List[float],
        min_samples: int = 10,
        classification: ClassificationMethods | None = None,
    ):
        self.segment_threshs = segment_thresholds
        self.min_samples = min_samples
        self.classification = classification or ClassificationMethods()
        # for RLELists
        self.segment_sums = [0.0] * len(segment_thresholds)
        self.segment_counts = [0] * len(segment_thresholds)
        self.n_segments = len(self.segment_threshs)
        # for lists
        self.segment_means: List[float] = []
        # Transient, rebuilt by every verdicts() call: one human-readable line
        # per enabled method, which is what the tracker's reason string is
        # assembled from. Never persisted -- it is derived from the series.
        self.last_details: Dict[str, str] = {}

    def _segment_boundaries(self, total_len: int, timestamps: List[float] | None = None) -> List[int]:
        """Index boundaries of n_segments segments over total_len items.

        Equal-index by default: each segment holds the same number of
        observations. When timestamps are given (one per item, non-decreasing,
        non-zero span), boundaries are equal-DURATION cuts of the observed time
        span, mapped back to indices. Falls back to equal-index whenever
        ``_timestamps_usable`` says no. A duration cut that leaves a segment
        empty is kept as-is: nothing observed in that window means no changes
        in it, which ``is_stable`` scores as a mean of 0.0.
        """
        segment_size = total_len / self.n_segments
        index_boundaries = [int(i * segment_size) for i in range(self.n_segments + 1)]
        index_boundaries[-1] = total_len
        if timestamps is None or not _timestamps_usable(timestamps, total_len):
            return index_boundaries
        t_first, t_last = timestamps[0], timestamps[-1]
        cuts = [
            t_first + k * (t_last - t_first) / self.n_segments
            for k in range(self.n_segments + 1)
        ]
        boundaries = [int(np.searchsorted(timestamps, t, side="left")) for t in cuts]
        boundaries[0] = 0
        boundaries[-1] = total_len
        return boundaries

    def _segment_verdict(
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
        occurrences means no changes.
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

    def verdicts(
        self,
        change_series: RLEList[bool] | List[bool],
        timestamps: List[float] | None = None,
    ) -> Dict[str, bool]:
        """Per-method stability verdicts, enabled methods only.

        Keys are the method names as they appear in the config block --
        "index", "time", "slope_index", "slope_time" -- in block order, so a
        reason string built by iterating this dict reads the same way every
        time.

        Every enabled method runs; there is no short-circuit. A combined
        verdict is only debuggable if the note carries all of the evidence,
        and ``last_details`` is populated here for exactly that.

        ``timestamps`` is threaded through only to the two time-axis methods,
        ``time`` and ``slope_time``; ``index`` and ``slope_index`` never see
        it. A caller who supplies ``timestamps`` without enabling either
        time-axis method gets index-axis results with no error and no
        warning.
        """
        self.last_details = {}
        self.segment_means = []
        out: Dict[str, bool] = {}
        empty = len(change_series) == 0
        for name in self.classification.enabled:
            if name in ("index", "time"):
                stamps = timestamps if name == "time" else None
                stable = self._segment_verdict(change_series, timestamps=stamps)
                self.last_details[name] = (
                    f"{name}: means {self.segment_means} "
                    f"{'below' if stable else 'exceed'} thresholds "
                    f"{self.segment_threshs} -> {'STABLE' if stable else 'UNSTABLE'}"
                )
            else:
                stamps = timestamps if name == "slope_time" else None
                if empty:
                    # Matches the segment methods: an empty series has nothing
                    # that could have changed, so nothing failed.
                    stable, k, axis = True, 0.0, "index"
                else:
                    k, axis = self._slope(change_series, stamps)
                    stable = k <= self.classification.slope_threshold
                self.last_details[name] = (
                    f"{name}: centroid {k:+.3f} ({axis} axis) "
                    f"{'at or below' if stable else 'above'} slope_threshold "
                    f"{self.classification.slope_threshold} -> "
                    f"{'STABLE' if stable else 'UNSTABLE'}"
                )
            out[name] = stable
        return out

    def decide(self, verdicts: Dict[str, bool]) -> bool:
        """Combine per-method verdicts under the configured decision rule.

        ``consensus`` requires every method; ``majority`` requires strictly
        more than half, so a tie resolves to UNSTABLE. The two agree at one
        and two enabled methods and diverge at three and four.
        """
        if not verdicts:
            # Unreachable via the config: ClassificationMethods rejects an
            # empty method set. Guards direct construction.
            return True
        n_stable = sum(verdicts.values())
        if self.classification.decision == "consensus":
            return n_stable == len(verdicts)
        return n_stable * 2 > len(verdicts)

    def is_stable(
        self,
        change_series: RLEList[bool] | List[bool],
        timestamps: List[float] | None = None,
    ) -> bool:
        """Combined stability verdict under the configured methods.

        ``timestamps`` are forwarded only to whichever enabled methods read
        the time axis (``time``, ``slope_time`` -- see ``verdicts()``). With
        only index-axis methods enabled, passing ``timestamps`` here has no
        effect and the call classifies exactly as if they were omitted.
        """
        return self.decide(self.verdicts(change_series, timestamps=timestamps))

    def get_last_details(self) -> Dict[str, str]:
        """One line per method from the last verdicts() call."""
        return self.last_details

    def slope(
        self,
        change_series: RLEList[bool] | List[bool],
        timestamps: List[float] | None = None,
    ) -> float:
        """Change centroid: where in the series the changes sit, in [-0.5, +0.5].

        The mean position of the changes, measured against the midpoint of the
        range those changes could occupy and scaled by its half-span. -0.5 is
        every change at the earliest countable position, 0 is uniform churn,
        +0.5 is every change at the very end.

        With no usable timestamps the position is the index ``p``::

            k = (p_bar - n/2) / (n - 2)

        With usable timestamps it is normalized time ``u``, measured against
        the range still reachable once index 0 is excluded::

            u       = (t - t_first) / (t_last - t_first)
            u_first = (t_1 - t_first) / (t_last - t_first)
            k       = (u_bar - (u_first + 1) / 2) / (1 - u_first)

        Substituting evenly spaced stamps collapses the second form into the
        first, so the two axes agree exactly on uniformly stamped data. That
        is what lets both slope methods share one threshold.

        Index 0 is excluded on both axes: the first value is always recorded as
        a change, so counting it would drag every variable negative, a
        perfectly static one included. On the time axis that exclusion is also
        why the denominator is the achievable range and not the full span.

        The index form is the least-squares slope over the same series with its
        data-free parts divided out -- for evenly spaced x the OLS denominator
        is the constant n(n-1)(n-2)/12, and the numerator collapses to
        m(p_bar - n/2) because only the change positions survive the binary y.
        The two are related by ``k_OLS = k * 12m / n(n-1)``, a strictly
        positive factor, so they never disagree on sign. Dropping the leading
        ``m`` is the point: it is what makes k comparable between events
        instead of scaling with how many changes happened to occur.

        Runs close in form, so an RLEList costs one pass over ``runs()`` with
        no expansion. Returns 0.0 when the series is too short to have a span,
        and -0.5 when nothing ever changed.
        """
        return self._slope(change_series, timestamps)[0]

    def _slope(
        self,
        change_series: RLEList[bool] | List[bool],
        timestamps: List[float] | None = None,
    ) -> tuple[float, str]:
        """``slope()`` plus the axis it actually used, for the reason string.

        The axis is not always the one configured: ``slope_time`` degrades to
        the index axis on unusable timestamps, and a note that did not say so
        would be misleading.
        """
        n = len(change_series)
        if n < 3:
            return 0.0, "index"
        # One narrowed local carries "use the time axis" and the stamps
        # together, so the two can never drift apart.
        stamps = timestamps
        if stamps is not None and not _timestamps_usable(stamps, n):
            stamps = None
        if stamps is not None:
            span = stamps[-1] - stamps[0]
            u_first = (stamps[1] - stamps[0]) / span
            # Every countable position shares one instant: no range to
            # normalize against, so fall back rather than divide by zero.
            if u_first >= 1.0:
                stamps = None
        runs = (
            change_series.runs() if isinstance(change_series, RLEList)
            else ((value, 1) for value in change_series)
        )
        position_sum, n_changes, position = 0.0, 0, 0
        for value, count in runs:
            if value:
                start = max(position, 1)  # index 0 is excluded
                length = position + count - start
                if length > 0:
                    if stamps is not None:
                        # Per-element accumulation required: summing a multi-element
                        # run with np.sum() changes order of operations vs. processing
                        # individual elements, breaking bit-identical agreement between
                        # RLEList and plain-list code paths.
                        for i in range(start, start + length):
                            position_sum += float(stamps[i])
                    else:
                        # sum of start .. start+length-1
                        position_sum += length * start + length * (length - 1) // 2
                    n_changes += length
            position += count
        if n_changes == 0:
            return -0.5, "time" if stamps is not None else "index"
        mean_position = position_sum / n_changes
        if stamps is not None:
            span = stamps[-1] - stamps[0]
            u_bar = (mean_position - stamps[0]) / span
            u_first = (stamps[1] - stamps[0]) / span
            return (u_bar - (u_first + 1) / 2) / (1 - u_first), "time"
        return (mean_position - n / 2) / (n - 2), "index"

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
            f"classification={self.classification}, "
            f"segment_means={self.segment_means})"
        )
