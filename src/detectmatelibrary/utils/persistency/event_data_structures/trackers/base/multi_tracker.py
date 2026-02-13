from typing import Any, Dict, Type

from detectmatelibrary.utils.preview_helpers import format_dict_repr

from .single_tracker import SingleTracker, Classification


class MultiTracker:
    """Tracks multiple features (e.g. variables or variable combos) using
    individual trackers."""

    def __init__(self, single_tracker_type: Type[SingleTracker] = SingleTracker) -> None:
        self.single_trackers: Dict[str, SingleTracker] = {}
        self.single_tracker_type: Type[SingleTracker] = single_tracker_type

    def add_data(self, data_object: Dict[str, Any]) -> None:
        """Add data to the appropriate feature trackers."""
        for name, value in data_object.items():
            if name not in self.single_trackers:
                self.single_trackers[name] = self.single_tracker_type()
            self.single_trackers[name].add_value(value)

    def get_trackers(self) -> Dict[str, SingleTracker]:
        """Get the current feature trackers."""
        return self.single_trackers

    def classify(self) -> Dict[str, Classification]:
        """Classify all tracked features."""
        classifications = {}
        for name, tracker in self.single_trackers.items():
            classifications[name] = tracker.classify()
        return classifications

    def __repr__(self) -> str:
        strs = format_dict_repr(self.single_trackers, indent="\t")
        return f"{self.__class__.__name__}{{\n\t{strs}\n}}\n"
