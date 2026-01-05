# from src.detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode
from abc import ABC, abstractmethod
from typing import Any, Dict, Set, Type

from detectmatelibrary.utils.RLE_list import RLEList
from detectmatelibrary.utils.preview_helpers import list_preview_str, format_dict_repr

from .base import EventDataStructure


class BaseTracker(ABC):
    @abstractmethod
    def extract_feature(self, value: Any) -> Any: ...

    @abstractmethod
    def add_value(self, value: Any) -> None: ...

    @abstractmethod
    def classify(self) -> Any: ...


class ConvergenceTracker(BaseTracker):
    """Tracks whether a variable is converging to a constant value."""

    def __init__(self, min_samples: int = 3) -> None:
        self.min_samples = min_samples
        self.series: RLEList[bool] = RLEList()
        self.value_set: Set[Any] = set()

    def extract_feature(self, value: Any) -> bool:
        """Extracts a feature from the value to track.

        Simply tracks whether the value is new (not seen before).
        """
        return True if value not in self.value_set else False

    def add_value(self, value: Any) -> None:
        """Add a new value to the tracker."""
        self.series.append(self.extract_feature(value))
        self.value_set.add(value)

    def classify(self) -> str:
        """Classify the variable as 'constant', 'random', or 'between'."""
        if len(self.series) < self.min_samples:
            return "not_enough_data"
        elif len(self.value_set) == 1:
            return "static"
        elif len(self.value_set) == len(self.series):
            return "random"
        # elif XY:
        #     return "stable"
        else:
            return "unstable"

    def __repr__(self) -> str:
        # show only part of the series for brevity
        series_str = list_preview_str(self.series)
        value_set_str = "{" + ", ".join(map(str, list_preview_str(self.value_set))) + "}"
        RLE_str = list_preview_str(self.series.runs())
        return (
            f"ConvergenceTracker(classification={self.classify()}, series={series_str}, "
            f"value_set={value_set_str}, RLE={RLE_str})"
        )


class VariableTrackers:
    """Tracks multiple variables using individual trackers."""

    def __init__(self, tracker_type: Type[BaseTracker] = ConvergenceTracker) -> None:
        self.trackers: Dict[str, BaseTracker] = {}
        self.tracker_type: Type[BaseTracker] = tracker_type

    def add_data(self, data_object: Dict[str, Any]) -> None:
        """Add data to the appropriate variable trackers."""
        for var_name, value in data_object.items():
            if var_name not in self.trackers:
                self.trackers[var_name] = self.tracker_type()
            self.trackers[var_name].add_value(value)

    def get_trackers(self) -> Dict[str, BaseTracker]:
        """Get the current variable trackers."""
        return self.trackers

    def classify(self) -> Dict[str, Any]:
        """Classify all tracked variables."""
        classifications = {}
        for var_name, tracker in self.trackers.items():
            classifications[var_name] = tracker.classify()
        return classifications

    def __repr__(self) -> str:
        strs = format_dict_repr(self.trackers, indent="\t")
        return f"VariableTrackers{{\n\t{strs}\n}}\n"


class EventVariableTracker(EventDataStructure):
    """Event data structure that tracks variable behaviors over time (or event
    series)."""

    def __init__(self) -> None:
        self.variable_trackers = VariableTrackers()
        self.current_data = None

    def add_data(self, data_object: Any) -> None:
        """Add data to the variable trackers."""
        self.variable_trackers.add_data(data_object)

    def get_data(self) -> Any:
        return self.variable_trackers.get_trackers()

    def get_variables(self) -> list[str]:
        return list(self.variable_trackers.get_trackers().keys())

    @staticmethod
    def to_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return raw_data

    def __repr__(self) -> str:
        strs = format_dict_repr(self.variable_trackers.get_trackers(), indent="\t")
        return f"EventVariableTracker(data={{\n\t{strs}\n}}"
