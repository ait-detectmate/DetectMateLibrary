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
        self.events_data: Dict[int | str, EventDataStructure] = {}
        self.events_seen: set[int | str] = set()
        self.event_data_class = event_data_class
        self.event_data_kwargs = event_data_kwargs or {}
        self.variable_blacklist = variable_blacklist or []
        self.event_templates: Dict[int | str, str] = {}
        self._dirty_count: int = 0

    def ingest_event(
        self,
        event_id: int | str,
        event_template: str,
        variables: list[Any] = [],
        named_variables: Dict[str, Any] = {}
    ) -> None:
        """Ingest event data into the appropriate EventData store."""
        self._dirty_count += 1
        self.events_seen.add(event_id)
        if not variables and not named_variables:
            return
        self.event_templates[event_id] = event_template
        all_variables = self.get_all_variables(variables, named_variables)

        data_structure = self.events_data.get(event_id)
        if data_structure is None:
            data_structure = self.event_data_class(**self.event_data_kwargs)
            self.events_data[event_id] = data_structure

        data = data_structure.to_data(all_variables)
        data_structure.add_data(data)

    def reset_dirty_count(self) -> None:
        """Reset the dirty counter after a successful save."""
        self._dirty_count = 0

    def get_events_seen(self) -> set[int | str]:
        """Retrieve all event IDs observed via ingest_event(), regardless of
        whether variables were extracted."""
        return self.events_seen

    def get_event_data(self, event_id: int | str) -> Any | None:
        """Retrieve the data for a specific event ID."""
        data_structure = self.events_data.get(event_id)
        return data_structure.get_data() if data_structure is not None else None

    def get_events_data(self) -> Dict[int | str, EventDataStructure]:
        """Retrieve the events data that is currently stored.

        Returns:
            A dictionary mapping event IDs to their corresponding EventDataStructure instances.

            Example:
            {
                1: EventTracker(data={
                    'var_0': SingleTracker(...),
                    'var_1': SingleTracker(...),
                }),
                2: EventTracker(data={
                    'var_0': SingleTracker(...)
                }),
                ...
            }
        """
        return self.events_data

    def get_event_template(self, event_id: int | str) -> str | None:
        """Retrieve the template for a specific event ID."""
        return self.event_templates.get(event_id)

    def get_event_templates(self) -> Dict[int | str, str]:
        """Retrieve all event templates."""
        return self.event_templates

    def get_all_variables(
        self,
        variables: list[Any],
        log_format_variables: Dict[str, Any],
        # variable_blacklist: List[str | int],
        event_var_prefix: str = "var_",
    ) -> dict[str, list[Any]]:
        """Combine log format variables and event variables into a single
        dictionary.

        Schema-friendly by using string column names.
        """
        all_vars: dict[str, list[Any]] = {
            k: v for k, v in log_format_variables.items()
            if k not in self.variable_blacklist
        }
        all_vars.update({
            f"{event_var_prefix}{i}": val for i, val in enumerate(variables)
            if i not in self.variable_blacklist
        })
        return all_vars

    def __getitem__(self, event_id: int | str) -> EventDataStructure | None:
        return self.events_data.get(event_id)

    def __repr__(self) -> str:
        return (
            f"EventPersistency(num_event_types={len(self.events_data)}, "
            f"keys={list(self.events_data.keys())})"
        )
