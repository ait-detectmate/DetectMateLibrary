"""Tracks whether a variable is converging to a constant value."""

import importlib
from functools import partial
from typing import Any, Callable, Dict, List, Literal, Set, TYPE_CHECKING
from detectmatelibrary.utils.preview_helpers import list_preview_str
from detectmatelibrary.utils.persistency.rle_list import RLEList
from ..base import SingleTracker, MultiTracker, EventTracker, Classification
from .stability_classifier import StabilityClassifier

if TYPE_CHECKING:
    from detectmatelibrary.common.detector import CoreDetectorConfig


def _strip_persist(detector_config: Any, method_id: str) -> Any:
    """Return a copy of a serialized detector_config with its persist section
    removed.

    A tracker reconstructs a throwaway detector from this config solely
    to recover its add_value_fn closure. If the config still carries
    persist, that throwaway instance starts a PersistencySaver --
    leaking a saver thread per variable and writing empty state over the
    real detector's file. No add_value_fn closure reads persist, so
    dropping it is behaviour-preserving.
    """
    if not isinstance(detector_config, dict):
        return detector_config
    detectors = detector_config.get("detectors")
    if not isinstance(detectors, dict):
        return detector_config
    entry = detectors.get(method_id)
    if not (isinstance(entry, dict) and "persist" in entry):
        return detector_config
    return {
        **detector_config,
        "detectors": {
            **detectors,
            method_id: {k: v for k, v in entry.items() if k != "persist"},
        },
    }


class SingleStabilityTracker(SingleTracker):
    """Tracks stability of a single feature."""

    def __init__(
        self,
        min_samples: int = 3,
        segmentation: Literal["count", "time", "both"] = "count",
        require_declining: bool = False,
        incline_threshold: float = -0.05,
        add_value_fn: str = "default",
        detector_config: "CoreDetectorConfig | None" = None,
    ) -> None:
        self.min_samples = min_samples
        self.segmentation = segmentation
        # Orthogonal to segmentation: an extra conjunct on STABLE, not another
        # way of cutting the series. See _is_stable().
        self.require_declining = require_declining
        self.change_series: RLEList[bool] = RLEList()
        self.unique_set: Set[Any] = set()
        self.stability_classifier: StabilityClassifier = StabilityClassifier(
            segment_thresholds=[1.1, 0.3, 0.1, 0.01],
            incline_threshold=incline_threshold,
        )
        # ponytail: O(N) timestamps; switch to fixed-width time buckets if
        # this ever runs unbounded/streaming.
        self.timestamps: List[float] = []
        # Opaque slot for detectors to stash per-variable model state that
        # must survive save/load. Schema-free; the tracker does not interpret it.
        self.extra_state: Dict[str, Any] = {}
        self.add_value_fn = add_value_fn
        self.detector_config = detector_config
        # Transient: set by _is_stable() as classify()'s reason string. Not
        # persisted -- it is derived from change_series on every classify().
        self._stability_note: str = ""
        self._value_fn: Callable[[Any], None] = self._default_add_value
        if add_value_fn != "default":
            detector_cls = getattr(importlib.import_module("detectmatelibrary.detectors"), add_value_fn)
            if detector_config is not None:
                detector = detector_cls(config=_strip_persist(detector_config, add_value_fn))
            else:
                detector = detector_cls()
            self._value_fn = partial(detector.add_value, self)

    def _default_add_value(self, value: Any) -> None:
        """Default value semantics: one set entry per whole value."""
        before = len(self.unique_set)
        self.unique_set.add(value)
        self.change_series.append(len(self.unique_set) > before)

    def add_value(self, value: Any, timestamp: float | None = None) -> None:
        """Add a new value to the tracker.

        Value semantics belong to ``_value_fn`` -- either the default above or a
        detector's ``add_value``. Timestamp bookkeeping stays here so
        ``timestamps`` cannot drift from ``change_series``: a detector may record
        nothing for a value (ValueRangeDetector on non-numeric input), and a
        length mismatch silently demotes the variable to count segmentation.
        """
        before = len(self.change_series)
        self._value_fn(value)
        if self.segmentation != "count" and timestamp is not None and len(self.change_series) > before:
            self.timestamps.append(float(timestamp))

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
        stable = self._is_stable()
        return Classification(
            type="STABLE" if stable else "UNSTABLE",
            reason=self._stability_note,
        )

    def _is_stable(self) -> bool:
        """Stability verdict under the configured segmentation.

        Builds ``_stability_note``, which is ``classify()``'s whole reason
        string -- the note has to name what actually failed, and with
        ``require_declining`` on that is no longer always the segment
        thresholds.

        ``both`` runs the count pass and the time pass over the same
        change series and requires both. Neither segmentation subsumes
        the other -- a variable that churns in a burst and then settles is
        count-UNSTABLE but time-STABLE, and one whose late churn is buried
        under a dense settled tail is the reverse -- so the conjunction is
        strictly stricter than either input.

        Deliberately not short-circuited: both passes always run so the
        note carries both mean vectors, which is what anyone debugging a
        ``both`` verdict needs. Costs one extra O(runs x n_segments) scan.
        """
        clf, ts = self.stability_classifier, self._aligned_timestamps()
        if self.segmentation != "both":
            verdict = clf.is_stable(self.change_series, timestamps=ts)
            note = f"Segment means of change series {clf.get_last_segment_means()}"
        else:
            count_stable = clf.is_stable(self.change_series)
            # Snapshot now, not after the time pass: is_stable() rebinds
            # clf.segment_means to a fresh list on every call, so calling
            # get_last_segment_means() after the time pass below would return
            # the time means for both halves of the note instead of the count
            # means it is meant to capture here.
            count_means = clf.get_last_segment_means()
            time_stable = clf.is_stable(self.change_series, timestamps=ts)
            note = (
                f"Segment means of change series: count {count_means}, "
                f"time {clf.get_last_segment_means()}"
            )
            verdict = count_stable and time_stable
        note += (
            f" {'are below' if verdict else 'exceed'} segment thresholds: "
            f"{clf.get_segment_thresholds()}"
        )
        if self.require_declining:
            k = clf.incline(self.change_series)
            declining = k <= clf.incline_threshold
            note += (
                f"; change centroid {k:+.3f} is "
                f"{'at or below' if declining else 'above'} the incline "
                f"threshold {clf.incline_threshold}"
            )
            verdict = verdict and declining
        self._stability_note = note
        return verdict

    def _aligned_timestamps(self) -> List[float] | None:
        """Timestamps to classify with, or None to fall back to count
        segments."""
        if self.segmentation != "count" and len(self.timestamps) == len(self.change_series):
            return self.timestamps
        return None

    def to_state(self) -> Dict[str, Any]:
        """Serialize tracker state to a plain dict (must be msgpack-
        compatible)."""
        return {
            "type": self.__class__.__name__,
            "module": self.__class__.__module__,
            "min_samples": self.min_samples,
            "segmentation": self.segmentation,
            "require_declining": self.require_declining,
            "incline_threshold": self.stability_classifier.incline_threshold,
            "timestamps": self.timestamps,
            "add_value_fn": self.add_value_fn,
            "detector_config": self.detector_config,
            "runs": self.change_series.runs(),
            "unique_set": list(self.unique_set),
            "segment_thresholds": self.stability_classifier.segment_threshs,
            "extra_state": self.extra_state,
        }

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "SingleStabilityTracker":
        """Restore tracker from a state dict produced by to_state()."""
        # Every optional key is read with .get(): a snapshot old enough to still
        # carry the removed `expand_value` predates `add_value_fn` too, so
        # indexing here would KeyError on exactly the states this tolerance is for.
        tracker = cls(
            min_samples=state["min_samples"],
            segmentation=state.get("segmentation", "count"),
            require_declining=state.get("require_declining", False),
            add_value_fn=state.get("add_value_fn", "default"),
            detector_config=state.get("detector_config"),
        )
        runs = [(bool(r[0]), int(r[1])) for r in state["runs"]]
        tracker.change_series._runs = runs
        tracker.change_series._len = sum(count for _, count in runs)
        tracker.unique_set = {
            tuple(v) if isinstance(v, list) else v for v in state["unique_set"]
        }
        tracker.stability_classifier = StabilityClassifier(
            segment_thresholds=state["segment_thresholds"],
            **({"incline_threshold": state["incline_threshold"]}
               if "incline_threshold" in state else {}),
        )
        tracker.timestamps = [float(t) for t in state.get("timestamps", [])]
        tracker.extra_state = state.get("extra_state", {})
        return tracker

    def __repr__(self) -> str:
        # show only part of the series for brevity
        series_str = list_preview_str(self.change_series)
        unique_set_str = "{" + ", ".join(map(str, list_preview_str(self.unique_set))) + "}"
        RLE_str = list_preview_str(self.change_series.runs())
        return (
            f"{self.__class__.__name__}(classification={self.classify()}, change_series={series_str}, "
            f"unique_set={unique_set_str}, RLE={RLE_str})"
        )


class MultiStabilityTracker(MultiTracker):
    """Tracks multiple features (e.g. variables or variable combos) using
    individual trackers."""

    def get_features_by_classification(
        self,
        classification_type: Literal["INSUFFICIENT_DATA", "STATIC", "RANDOM", "STABLE", "UNSTABLE"]
    ) -> List[str]:
        """Get a list of variable names that are classified as the given
        type."""
        variables = []
        for name, tracker in self.single_trackers.items():
            classification = tracker.classify()
            if classification.type == classification_type:
                variables.append(name)
        return variables


class EventStabilityTracker(EventTracker):
    """Event data structure that tracks the stability of each event over time /
    number of events."""

    def __init__(
        self,
        converter_function: Callable[[Any], Any] = lambda x: x,
        segmentation: Literal["count", "time", "both"] = "count",
        require_declining: bool = False,
        incline_threshold: float = -0.05,
        add_value_fn: str = "default",
        detector_config: "CoreDetectorConfig | None" = None

    ) -> None:
        self.multi_tracker: MultiStabilityTracker  # for type hinting

        def make_tracker() -> SingleStabilityTracker:
            return SingleStabilityTracker(
                segmentation=segmentation,
                require_declining=require_declining,
                incline_threshold=incline_threshold,
                add_value_fn=add_value_fn,
                detector_config=detector_config,
            )

        # Mirror class identity onto the closure so dump()/load() can resolve
        # the underlying SingleStabilityTracker via its module + qualname.
        make_tracker.__name__ = SingleStabilityTracker.__name__
        make_tracker.__module__ = SingleStabilityTracker.__module__

        super().__init__(
            single_tracker_type=make_tracker,
            multi_tracker_type=MultiStabilityTracker,
            converter_function=converter_function,
        )

    def get_features_by_classification(
        self, classification_type: Literal["INSUFFICIENT_DATA", "STATIC", "RANDOM", "STABLE", "UNSTABLE"]
    ) -> List[str]:
        """Get a list of variable names that are classified as the given
        type."""
        return self.multi_tracker.get_features_by_classification(classification_type)
