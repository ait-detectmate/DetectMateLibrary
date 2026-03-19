"""Event data structure that tracks variable behaviors over time/events."""

from typing import Any, Callable, Dict, Type

from detectmatelibrary.utils.preview_helpers import format_dict_repr

from .multi_tracker import MultiTracker
from .single_tracker import SingleTracker
from ...base import EventDataStructure


class EventTracker(EventDataStructure):
    """Event data structure that tracks the behavior of each event over time /
    number of events."""

    def __init__(
        self,
        single_tracker_type: Type[SingleTracker] = SingleTracker,
        multi_tracker_type: Type[MultiTracker] = MultiTracker,
        converter_function: Callable[[Any], Any] = lambda x: x,
    ) -> None:
        self.single_tracker_type = single_tracker_type
        self.multi_tracker_type = multi_tracker_type
        self.converter_function = converter_function
        self.multi_tracker = self.multi_tracker_type(single_tracker_type=self.single_tracker_type)

    def add_data(self, data_object: Any) -> None:
        """Add data to the variable trackers."""
        self.multi_tracker.add_data(data_object)

    def get_data(self) -> Dict[str, SingleTracker]:
        """Retrieve the tracker's stored data."""
        return self.multi_tracker.get_trackers()

    def get_variables(self) -> list[str]:
        """Get the list of tracked variable names."""
        return list(self.multi_tracker.get_trackers().keys())

    def to_data(self, raw_data: Dict[str, Any]) -> Any:
        """Transform raw data into the format expected by the tracker."""
        return self.converter_function(raw_data)

    def __repr__(self) -> str:
        strs = format_dict_repr(self.multi_tracker.get_trackers(), indent="\t")
        return f"{self.__class__.__name__}(data={{\n\t{strs}\n}})"
