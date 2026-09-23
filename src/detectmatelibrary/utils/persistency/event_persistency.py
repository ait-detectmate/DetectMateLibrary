from .basic_persistency import EventPersistencyBase

from typing import Any, Callable, Dict, List, Optional, Self
import threading
import json
import ast


class EventPersistency(EventPersistencyBase):
    """
    Event-based persistency orchestrator:
    - manages multiple EventDataStructure instances, one per event ID
    - doesn't know retention strategyvalue
    - only delegates to EventDataStructure

    Args:
        event_data_class: The EventDataStructure subclass to use for storing event data.
        variable_blacklist: Variable names to exclude from storage. "Content" is excluded by default.
        event_data_kwargs: Additional keyword arguments to pass to the EventDataStructure constructor.
    """

    def __init__(
        self,
        do_slow_per: bool = True,
        variable_blacklist: Optional[List[str | int]] = ["Content"],
        *,
        event_data_kwargs: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            do_slow_per=do_slow_per,
            variable_blacklist=variable_blacklist,
            event_data_kwargs=event_data_kwargs
        )
        self._on_ingest_callbacks: list[Callable[[], None]] = []
        # ponytail: RLock shared with PersistencySaver so ingest/save/load are
        # mutually exclusive. On-ingest callbacks fire outside this lock, so
        # re-entrancy is no longer required — kept as RLock (harmless, safer).
        self._lock = threading.RLock()

    def ingest_event(
        self,
        event_id: int | str,
        event_template: str,
        variables: list[Any] = [],
        named_variables: Dict[str, Any] = {},
        timestamp: float | None = None,
    ) -> None:
        """Ingest event data into the appropriate EventData store."""
        with self._lock:
            super().ingest_event(
                event_id=event_id,
                event_template=event_template,
                variables=variables,
                named_variables=named_variables,
                timestamp=timestamp
            )
        # ponytail: fire callbacks outside the lock so a count-triggered save
        # doesn't hold the ingest lock across serialize + file I/O.
        for _cb in self._on_ingest_callbacks:
            _cb()

    def register_on_ingest(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked after every ingest_event call."""
        self._on_ingest_callbacks.append(callback)

    def combine(self, other: "EventPersistency") -> Self:
        """Combine two Event persistency."""
        df = other.event_struct.get_data()
        for i in range(df.shape[0]):
            row = df.row(i, named=True)
            self.ingest_event(
                event_id=row["EventIDs"],
                event_template=row["Templates"],
                named_variables=json.loads(ast.literal_eval(row["Vars"]))
            )
        return self
