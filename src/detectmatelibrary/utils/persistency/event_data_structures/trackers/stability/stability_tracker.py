"""Tracks whether a variable is converging to a constant value."""

import importlib
from functools import partial
from typing import Any, Callable, Dict, List, Literal, Set, TYPE_CHECKING
from detectmatelibrary.utils.preview_helpers import list_preview_str
from detectmatelibrary.utils.persistency.rle_list import RLEList
from ..base import SingleTracker, MultiTracker, EventTracker, Classification
from .stability_classifier import StabilityClassifier
from .classification_methods import ClassificationMethods

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


def _as_methods(
    classification: "ClassificationMethods | Dict[str, Any] | None",
) -> ClassificationMethods:
    """Accept the block as a model, a plain dict, or nothing.

    to_state() writes a dict and the config layer forwards a dict, so the
    tracker has to take both without either caller converting first.

    Returns a copy when given a model instance: an ``EventStabilityTracker``
    shares one passed-in ``ClassificationMethods`` across every per-variable
    tracker it creates, so storing the caller's instance as-is would let a
    later in-place mutation of it silently change every variable already
    built from it.
    """
    if classification is None:
        return ClassificationMethods()
    if isinstance(classification, ClassificationMethods):
        return classification.model_copy()
    return ClassificationMethods(**classification)


def _classification_from_state(state: Dict[str, Any]) -> ClassificationMethods:
    """The classification block for a state dict, old or new.

    Legacy snapshots predate the four-method split. Their `segmentation`
    enum maps onto the two segment-threshold methods and `require_declining`
    onto `slope_index`; their semantics were always AND, so they decide by
    consensus. This is the only place the old names survive -- the config
    layer rejects them outright.
    """
    if "classification" in state:
        return ClassificationMethods(**state["classification"])
    segmentation = state.get("segmentation", "count")
    return ClassificationMethods(
        index=segmentation in ("count", "both"),
        time=segmentation in ("time", "both"),
        slope_index=bool(state.get("require_declining", False)),
        slope_threshold=state.get("incline_threshold", -0.05),
        decision="consensus",
    )


class SingleStabilityTracker(SingleTracker):
    """Tracks stability of a single feature."""

    def __init__(
        self,
        min_samples: int = 3,
        classification: "ClassificationMethods | Dict[str, Any] | None" = None,
        add_value_fn: str = "default",
        detector_config: "CoreDetectorConfig | None" = None,
    ) -> None:
        self.min_samples = min_samples
        self.change_series: RLEList[bool] = RLEList()
        self.unique_set: Set[Any] = set()
        self.stability_classifier: StabilityClassifier = StabilityClassifier(
            segment_thresholds=[1.1, 0.3, 0.1, 0.01],
            classification=_as_methods(classification),
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

    @property
    def classification(self) -> ClassificationMethods:
        """The classification methods in force, owned by the classifier.

        A property rather than a second attribute: the tracker reads it at
        ingest time (to decide whether to collect timestamps) and the
        classifier reads it at classify() time, and two copies would let
        those two drift apart. Reassignable between classify() calls -- the
        methods are read when classify() runs, never when values arrive, so
        several verdicts can be taken from one ingest by swapping this.
        """
        return self.stability_classifier.classification

    @classification.setter
    def classification(
        self, value: "ClassificationMethods | Dict[str, Any] | None"
    ) -> None:
        self.stability_classifier.classification = _as_methods(value)

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
        length mismatch silently leaves that value off the time axis, demoting
        the variable to index-based classification.
        """
        before = len(self.change_series)
        self._value_fn(value)
        if (
            self.classification.needs_timestamps
            and timestamp is not None
            and len(self.change_series) > before
        ):
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
        """Stability verdict under the configured classification methods.

        Builds ``_stability_note``, which is ``classify()``'s whole reason
        string. The note names every enabled method, what it found, and how
        the decision rule resolved -- with four selectable methods and two
        decision rules, naming only the verdict would leave a reader unable
        to tell which method drove it.
        """
        clf = self.stability_classifier
        verdicts = clf.verdicts(self.change_series, timestamps=self._aligned_timestamps())
        n_stable, n_total = sum(verdicts.values()), len(verdicts)
        verdict = clf.decide(verdicts)
        details = clf.get_last_details()
        self._stability_note = "; ".join(
            [details[name] for name in verdicts]
            + [f"decision={clf.classification.decision} ({n_stable}/{n_total}) -> "
               f"{'STABLE' if verdict else 'UNSTABLE'}"]
        )
        return verdict

    def _aligned_timestamps(self) -> List[float] | None:
        """Timestamps to classify with, or None to fall back to the index
        axis."""
        if (
            self.classification.needs_timestamps
            and len(self.timestamps) == len(self.change_series)
        ):
            return self.timestamps
        return None

    def to_state(self) -> Dict[str, Any]:
        """Serialize tracker state to a plain dict (must be msgpack-
        compatible)."""
        return {
            "type": self.__class__.__name__,
            "module": self.__class__.__module__,
            "min_samples": self.min_samples,
            "classification": self.classification.model_dump(),
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
        """Restore tracker from a state dict produced by to_state().

        Every optional key is read with .get(): a snapshot old enough to still
        carry the removed `expand_value` predates `add_value_fn` too, so
        indexing here would KeyError on exactly the states this tolerance is
        for. The same applies to the classification block -- snapshots written
        before the four-method split carry `segmentation` / `require_declining`
        / `incline_threshold` instead, and _classification_from_state
        translates them.
        """
        classification = _classification_from_state(state)
        tracker = cls(
            min_samples=state["min_samples"],
            classification=classification,
            add_value_fn=state.get("add_value_fn", "default"),
            detector_config=state.get("detector_config"),
        )
        runs = [(bool(r[0]), int(r[1])) for r in state["runs"]]
        tracker.change_series._runs = runs
        tracker.change_series._len = sum(count for _, count in runs)
        tracker.unique_set = {
            tuple(v) if isinstance(v, list) else v for v in state["unique_set"]
        }
        # Rebuilding the classifier drops the one __init__ made, so the block
        # is passed from the local -- reading tracker.classification here would
        # read through the very object being replaced.
        tracker.stability_classifier = StabilityClassifier(
            segment_thresholds=state["segment_thresholds"],
            classification=classification,
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
            f"{self.__class__.__name__}(verdict={self.classify()}, change_series={series_str}, "
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
        classification: "ClassificationMethods | Dict[str, Any] | None" = None,
        add_value_fn: str = "default",
        detector_config: "CoreDetectorConfig | None" = None,
    ) -> None:
        self.multi_tracker: MultiStabilityTracker  # for type hinting

        def make_tracker() -> SingleStabilityTracker:
            return SingleStabilityTracker(
                classification=classification,
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
