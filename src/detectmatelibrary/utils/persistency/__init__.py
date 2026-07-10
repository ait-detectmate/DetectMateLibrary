from typing import Any

from .event_persistency import EventPersistency
from .persistency_saver import PersistencySaver, PersistencySaverConfig, PersistencyLoadError, save, load
from .event_data_structures.base import EventDataStructure
from .event_data_structures.trackers.stability.stability_tracker import EventStabilityTracker

__all__ = [
    "EventPersistency",
    "PersistencySaver",
    "PersistencySaverConfig",
    "PersistencyLoadError",
    "EventDataStructure",
    "EventDataFrame",
    "ChunkedEventDataFrame",
    "EventStabilityTracker",
    "save",
    "load",
]

_DATAFRAME_EXPORTS = {"EventDataFrame", "ChunkedEventDataFrame"}


def __getattr__(name: str) -> Any:
    if name in _DATAFRAME_EXPORTS:
        try:
            from .event_data_structures.dataframes import EventDataFrame, ChunkedEventDataFrame
        except ImportError as e:
            raise ImportError(
                f"'{name}' requires the 'dataframes' extra: "
                "pip install 'detectmatelibrary[dataframes]'"
            ) from e
        globals()["EventDataFrame"] = EventDataFrame
        globals()["ChunkedEventDataFrame"] = ChunkedEventDataFrame
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
