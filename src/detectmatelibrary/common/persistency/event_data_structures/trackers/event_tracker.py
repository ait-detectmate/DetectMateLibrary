"""Event data structure that tracks variable behaviors over time/events."""

from typing import Any, Dict, Type, List, Literal
from dataclasses import dataclass, field

from detectmatelibrary.utils.preview_helpers import format_dict_repr

from ..base import EventDataStructure
from .single_trackers.stability_tracker import StabilityTracker
from .multi_tracker import MultiTracker
from .converter import Converter, InvariantConverter, ComboConverter


@dataclass
class EventTracker(EventDataStructure):
    """Event data structure that tracks the behavior of each event over time /
    number of events."""

    tracker_type: Type[StabilityTracker] = StabilityTracker
    multi_tracker: MultiTracker = field(init=False)
    feature_type: Literal["variable", "variable_combo"] = "variable"
    converter: Converter = field(init=False)

    def __post_init__(self) -> None:
        self.multi_tracker = MultiTracker(tracker_type=self.tracker_type)

        if self.feature_type == "variable":
            self.converter = InvariantConverter()
        elif self.feature_type == "variable_combo":
            self.converter = ComboConverter()
        else:
            raise ValueError(f"Invalid feature: {self.feature_type}")

    def add_data(self, data_object: Any) -> None:
        """Add data to the variable trackers."""
        self.multi_tracker.add_data(data_object)

    def get_data(self) -> Any:
        """Retrieve the tracker's stored data."""
        return self.multi_tracker.get_trackers()

    def get_variables(self) -> list[str]:
        """Get the list of tracked variable names."""
        return list(self.multi_tracker.get_trackers().keys())

    def get_variables_by_classification(
        self, classification_type: Literal["INSUFFICIENT_DATA", "STATIC", "RANDOM", "STABLE", "UNSTABLE"]
    ) -> List[str]:
        """Get a list of variable names that are classified as the given
        type."""
        return self.multi_tracker.get_variables_by_classification(classification_type)

    def to_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw data into the format expected by the tracker."""
        return self.converter.convert(raw_data)

    def __repr__(self) -> str:
        strs = format_dict_repr(self.multi_tracker.get_trackers(), indent="\t")
        return f"{self.__class__.__name__}(data={{\n\t{strs}\n}})"
