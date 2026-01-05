from typing import Any, Dict, Optional, Type

from .event_data_structures.base import EventDataStructure


# -------- Generic persistency --------

class EventPersistency:
    """
    Event-based persistency orchestrator:
    - manages multiple EventDataStructure instances, one per event ID
    - doesn't know retention strategy
    - only delegates to EventDataStructure
    """

    def __init__(
        self,
        event_data_class: Type[EventDataStructure],
        variable_blacklist: Optional[set[str | int]] = None,
        *,
        event_data_kwargs: Optional[dict[str, Any]] = None,
    ):
        self.events_data: Dict[int, EventDataStructure] = {}
        self.event_data_class = event_data_class
        self.event_data_kwargs = event_data_kwargs or {}
        self.variable_blacklist = variable_blacklist or set()

    def ingest_event(
        self,
        event_id: int,
        variables: list[Any],
        log_format_variables: Dict[str, Any],
    ) -> None:
        """Ingest event data into the appropriate EventData store."""
        all_variables = self.get_all_variables(variables, log_format_variables, self.variable_blacklist)
        data = self.event_data_class.to_data(all_variables)

        data_structure = self.events_data.get(event_id)
        if data_structure is None:
            data_structure = self.event_data_class(**self.event_data_kwargs)
            self.events_data[event_id] = data_structure

        data_structure.add_data(data)

    def get_event_data(self, event_id: int) -> Any | None:
        """Retrieve the data for a specific event ID."""
        data_structure = self.events_data.get(event_id)
        return data_structure.get_data() if data_structure is not None else None

    @staticmethod
    def get_all_variables(
        variables: list[Any],
        log_format_variables: Dict[str, Any],
        variable_blacklist: set[str | int],
        event_var_prefix: str = "var_",
    ) -> dict[str, list[Any]]:
        """Combine log format variables and event variables into a single
        dictionary.

        Schema-friendly by using string column names.
        """
        all_vars: dict[str, list[Any]] = {
            k: v for k, v in log_format_variables.items()
            if k not in variable_blacklist
        }
        all_vars.update({
            f"{event_var_prefix}{i}": val for i, val in enumerate(variables)
            if i not in variable_blacklist
        })
        return all_vars

    def __getitem__(self, event_id: int) -> EventDataStructure | None:
        return self.events_data.get(event_id)

    def __repr__(self) -> str:
        return f"EventPersistency(num_event_types={len(self.events_data)})"
