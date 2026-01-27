from typing import Any, Dict, Type, List, Literal

from detectmatelibrary.utils.preview_helpers import format_dict_repr

from .single_trackers.base import SingleTracker


class MultiTracker:
    """Tracks multiple features (e.g. variables or variable combos) using
    individual trackers."""

    def __init__(self, tracker_type: Type[SingleTracker] = SingleTracker) -> None:
        self.trackers: Dict[str, SingleTracker] = {}
        self.tracker_type: Type[SingleTracker] = tracker_type

    def add_data(self, data_object: Dict[str, Any]) -> None:
        """Add data to the appropriate feature trackers."""
        for name, value in data_object.items():
            if name not in self.trackers:
                self.trackers[name] = self.tracker_type()
            self.trackers[name].add_value(value)

    def get_trackers(self) -> Dict[str, SingleTracker]:
        """Get the current feature trackers."""
        return self.trackers

    def classify(self) -> Dict[str, Any]:
        """Classify all tracked features."""
        classifications = {}
        for name, tracker in self.trackers.items():
            classifications[name] = tracker.classify()
        return classifications

    def get_variables_by_classification(
        self,
        classification_type: Literal["INSUFFICIENT_DATA", "STATIC", "RANDOM", "STABLE", "UNSTABLE"]
    ) -> List[str]:
        """Get a list of variable names that are classified as the given
        type."""
        variables = []
        for name, tracker in self.trackers.items():
            classification = tracker.classify()
            if classification.type == classification_type:
                variables.append(name)
        return variables

    def __repr__(self) -> str:
        strs = format_dict_repr(self.trackers, indent="\t")
        return f"{self.__class__.__name__}{{\n\t{strs}\n}}\n"
