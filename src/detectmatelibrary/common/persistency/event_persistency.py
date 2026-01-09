from typing import Any, Dict, List, Optional, Type

from .event_data_structures.base import EventDataStructure


# -------- Generic persistency --------

class EventPersistency:
    """
    Event-based persistency orchestrator:
    - manages multiple EventDataStructure instances, one per event ID
    - doesn't know retention strategy
    - only delegates to EventDataStructure

    Args:
        event_data_class: The EventDataStructure subclass to use for storing event data.
        variable_blacklist: Variable names to exclude from storage. "Content" is excluded by default.
        event_data_kwargs: Additional keyword arguments to pass to the EventDataStructure constructor.
    """

    def __init__(
        self,
        event_data_class: Type[EventDataStructure],
        variable_blacklist: Optional[List[str | int]] = ["Content"],
        *,
        event_data_kwargs: Optional[dict[str, Any]] = None,
    ):
        self.events_data: Dict[int, EventDataStructure] = {}
        self.event_data_class = event_data_class
        self.event_data_kwargs = event_data_kwargs or {}
        self.variable_blacklist = variable_blacklist or []
        self.event_templates: Dict[int, str] = {}

    def ingest_event(
        self,
        event_id: int,
        event_template: str,
        variables: list[Any],
        log_format_variables: Dict[str, Any],
    ) -> None:
        """Ingest event data into the appropriate EventData store."""
        self.event_templates[event_id] = event_template
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

    def get_events_data(self) -> Any | None:
        """Retrieve the events' data."""
        return self.events_data

    def get_event_template(self, event_id: int) -> str | None:
        """Retrieve the template for a specific event ID."""
        return self.event_templates.get(event_id)

    def get_event_templates(self) -> Dict[int, str]:
        """Retrieve all event templates."""
        return self.event_templates

    @staticmethod
    def get_all_variables(
        variables: list[Any],
        log_format_variables: Dict[str, Any],
        variable_blacklist: List[str | int],
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
        return (
            f"EventPersistency(num_event_types={len(self.events_data)}, "
            f"keys={list(self.events_data.keys())})"
        )
