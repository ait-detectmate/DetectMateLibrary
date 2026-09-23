from .data_structures.trackers import EventStabilityTracker
from .slow_persistency import SlowPersistency

from typing import Any, Dict, List, Optional
import warnings
import polars as pl
import json


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


class PersistencyStruct:
    """Event structure of the Event Persistency."""
    def __init__(
        self,
        do_slow_pers: bool = False,
        event_data_kwargs: Optional[dict[str, Any]] = None,
    ) -> None:
        self.fast_persistency: Dict[int | str, EventStabilityTracker] = {}
        self.data_kwargs = event_data_kwargs or {}
        self.templates: Dict[int | str, str] = {}
        self.do_slow = do_slow_pers

        self.columns: list[str] = ["EventIDs", "Templates", "Timestamps", "Vars"]
        if self.do_slow:
            self.slow_persistency = SlowPersistency(self.columns)

    def __contains__(self, event_id: int | str) -> bool:
        return event_id in self.fast_persistency

    def __getitem__(self, event_id: int | str) -> EventStabilityTracker | None:
        return self.fast_persistency.get(event_id, None)

    def get_events(self) -> list[int | str]:
        return list(self.fast_persistency.keys())

    def update_data_structure(
        self,
        event_id: int | str,
        variables: dict[str, list[Any]],
        template: str,
        timestamp: float | None
    ) -> None:

        if len(variables) > 0:
            self.templates[event_id] = template
            if event_id not in self:
                self.fast_persistency[event_id] = EventStabilityTracker(**self.data_kwargs)
            self[event_id].add_data(variables, timestamp=timestamp, do_preprocess=True)  # type: ignore

        if self.do_slow:
            self.slow_persistency.add(
                [event_id, template, timestamp, json.dumps(variables).encode("utf-8")]
            )

    def get_template(self, event_id: int | str) -> str | None:
        return self.templates.get(event_id, None)

    def __len__(self) -> int:
        return len(self.fast_persistency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PersistencyStruct) or len(self) != len(other):
            return False
        for elem1, elem2 in zip(self.fast_persistency.values(), other.fast_persistency.values()):
            if elem1.as_dict() != elem2.as_dict():
                return False

        return True

    def get_data(self) -> pl.DataFrame:
        if self.do_slow:
            self.slow_persistency.push_buffer()
            return self.slow_persistency.load()
        return pl.DataFrame([])

    def overwrite_slow(self, df: pl.DataFrame) -> None:
        if self.do_slow:
            self.slow_persistency = SlowPersistency.from_dataframe(df)
        else:
            warnings.warn("Slow persistency was disable")


class EventPersistencyBase:
    """Event Persistency without lock protection."""
    def __init__(
        self,
        do_slow_per: bool = True,
        variable_blacklist: Optional[List[str | int]] = ["Content"],
        *,
        event_data_kwargs: Optional[dict[str, Any]] = None,
    ):
        self.event_struct = PersistencyStruct(
            event_data_kwargs=event_data_kwargs, do_slow_pers=do_slow_per
        )

        self.events_seen: set[int | str] = set()
        self.variable_blacklist = variable_blacklist or []
        self._events_since_save: int = 0

    def get_all_variables(
        self, variables: list[Any], log_format_variables: Dict[str, Any], event_var_prefix: str = "var_",
    ) -> dict[str, list[Any]]:
        return get_all_variables(
            variables=variables,
            log_format_variables=log_format_variables,
            variable_blacklist=self.variable_blacklist,
            event_var_prefix=event_var_prefix
        )

    def ingest_event(
        self,
        event_id: int | str,
        event_template: str,
        variables: list[Any] = [],
        named_variables: Dict[str, Any] = {},
        timestamp: float | None = None,
    ) -> None:
        self._events_since_save += 1
        self.events_seen.add(event_id)
        all_variables = self.get_all_variables(variables, named_variables)

        self.event_struct.update_data_structure(
            event_id, variables=all_variables, template=event_template, timestamp=timestamp
        )

    @property
    def events_since_save(self) -> int:
        """Number of events ingested since the last successful save."""
        return self._events_since_save

    def reset_events_since_save(self) -> None:
        """Reset the events-since-save counter after a successful save."""
        self._events_since_save = 0

    def get_events_seen(self) -> set[int | str]:
        """Retrieve all event IDs observed via ingest_event(), regardless of
        whether variables were extracted."""
        return self.events_seen

    def get_event_data(self, event_id: int | str) -> Any | None:
        """Retrieve the data for a specific event ID."""
        return d_struct.get_data() if (d_struct := self.event_struct[event_id]) is not None else None

    def get_events_data(self) -> Dict[int | str, EventStabilityTracker]:
        """Retrieve the events data that is currently stored."""
        return self.event_struct.fast_persistency

    def get_event_template(self, event_id: int | str) -> str | None:
        """Retrieve the template for a specific event ID."""
        return self.event_struct.get_template(event_id)

    def get_event_templates(self) -> Dict[int | str, str]:
        """Retrieve all event templates."""
        return self.event_struct.templates

    def __getitem__(self, event_id: int | str) -> EventStabilityTracker | None:
        return self.event_struct[event_id]

    def __repr__(self) -> str:
        return (
            f"EventPersistency(num_event_types={len(self.event_struct.fast_persistency)}, "
            f"keys={list(self.event_struct.fast_persistency.keys())})"
        )

    def __len__(self) -> int:
        return len(self.event_struct)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventPersistencyBase) or len(self) != len(other):
            return False
        return self.events_seen == other.events_seen and self.event_struct == other.event_struct
