"""Tracks whether a variable is converging to a constant value."""

import importlib
from typing import Any, Callable, Dict, List, Literal, Set, TYPE_CHECKING
from detectmatelibrary.utils.preview_helpers import list_preview_str
from detectmatelibrary.utils.persistency.rle_list import RLEList
from ..base import SingleTracker, MultiTracker, EventTracker, Classification
from .stability_classifier import StabilityClassifier

if TYPE_CHECKING:
    from detectmatelibrary.common.detector import CoreDetectorConfig


class SingleStabilityTracker(SingleTracker):
    """Tracks stability of a single feature."""

    def __init__(self, min_samples: int = 3, add_value_fn: str = "default",
                 detector_config: "CoreDetectorConfig | None" = None) -> None:
        self.min_samples = min_samples
        self.change_series: RLEList[bool] = RLEList()
        self.unique_set: Set[Any] = set()
        self.stability_classifier: StabilityClassifier = StabilityClassifier(
            segment_thresholds=[1.1, 0.3, 0.1, 0.01],
        )
        # Opaque slot for detectors to stash per-variable model state that
        # must survive save/load. Schema-free; the tracker does not interpret it.
        self.extra_state: Dict[str, Any] = {}
        self.add_value_fn = add_value_fn
        self.detector_config = detector_config
        if add_value_fn != "default":
            detector = getattr(importlib.import_module("detectmatelibrary.detectors"), add_value_fn)
            if detector_config is not None:
                detector = detector(config=detector_config)
            else:
                detector = detector()
            self.add_value = detector.add_value_fn.__get__(self, type(self))  # type: ignore[method-assign]

    def add_value(self, value: Any, timestamp: float | None = None) -> None:
        """Add a new value to the tracker."""
        before = len(self.unique_set)
        self.unique_set.add(value)
        self.change_series.append(len(self.unique_set) > before)
        if self.time_dependent and timestamp is not None:
            self.timestamps.append(float(timestamp))

    def classify(self) -> Classification:
        """Classify the variable."""
        timestamps = (
            self.timestamps
            if self.time_dependent and len(self.timestamps) == len(self.change_series)
            else None
        )
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
        elif self.stability_classifier.is_stable(self.change_series, timestamps=timestamps):
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

    def to_state(self) -> Dict[str, Any]:
        """Serialize tracker state to a plain dict (must be msgpack-
        compatible)."""
        return {
            "type": self.__class__.__name__,
            "module": self.__class__.__module__,
            "min_samples": self.min_samples,
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
        tracker = cls(
            min_samples=state["min_samples"],
            add_value_fn=state["add_value_fn"],
            detector_config=state["detector_config"]
        )
        runs = [(bool(r[0]), int(r[1])) for r in state["runs"]]
        tracker.change_series._runs = runs
        tracker.change_series._len = sum(count for _, count in runs)
        tracker.unique_set = {
            tuple(v) if isinstance(v, list) else v for v in state["unique_set"]
        }
        tracker.stability_classifier = StabilityClassifier(
            segment_thresholds=state["segment_thresholds"]
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
        add_value_fn: str = "default",
        detector_config: "CoreDetectorConfig | None" = None

    ) -> None:
        self.multi_tracker: MultiStabilityTracker  # for type hinting

        def make_tracker() -> SingleStabilityTracker:
            return SingleStabilityTracker(add_value_fn=add_value_fn, detector_config=detector_config)

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
