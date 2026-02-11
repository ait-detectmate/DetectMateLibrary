from pydantic import BaseModel

from typing_extensions import Self
from typing import Dict, Any


# Sub-formats ********************************************************+
class Variable(BaseModel):
    pos: int
    name: str
    params: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert Variable to YAML-compatible dictionary."""
        result: Dict[str, Any] = {
            "pos": self.pos,
            "name": self.name,
        }
        if self.params:
            result["params"] = self.params
        return result


class Header(BaseModel):
    pos: str
    params: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert Header to YAML-compatible dictionary."""
        result: Dict[str, Any] = {
            "pos": self.pos,
        }
        if self.params:
            result["params"] = self.params
        return result


class _EventInstance(BaseModel):
    """Configuration for a specific instance within an event."""
    params: Dict[str, Any] = {}
    variables: Dict[int, Variable] = {}
    header_variables: Dict[str, Header] = {}

    @classmethod
    def _init(cls, **kwargs: dict[str, Any]) -> "_EventInstance":
        for var, cl in zip(["variables", "header_variables"], [Variable, Header]):
            if var in kwargs:
                new_dict = {}
                for v in kwargs[var]:
                    aux = cl(**v)  # type: ignore
                    new_dict[aux.pos] = aux
                kwargs[var] = new_dict
        return cls(**kwargs)  # type: ignore

    def get_all(self) -> Dict[Any, Header | Variable]:
        return {**self.variables, **self.header_variables}

    def to_dict(self) -> Dict[str, Any]:
        """Convert _EventInstance to YAML-compatible dictionary."""
        result: Dict[str, Any] = {}
        # Always include params even if empty (to match YAML structure)
        result["params"] = self.params
        if self.variables:
            result["variables"] = [var.to_dict() for var in self.variables.values()]
        if self.header_variables:
            result["header_variables"] = [header.to_dict() for header in self.header_variables.values()]
        return result


class _EventConfig(BaseModel):
    """Configuration for all instances of a specific event."""
    instances: Dict[str, _EventInstance]

    @classmethod
    def _init(cls, instances_dict: Dict[str, Dict[str, Any]]) -> "_EventConfig":
        instances = {}
        for instance_id, instance_data in instances_dict.items():
            instances[instance_id] = _EventInstance._init(**instance_data)
        return cls(instances=instances)

    @property
    def variables(self) -> Dict[int, Variable]:
        """Pass-through to first instance for compatibility."""
        if self.instances:
            return next(iter(self.instances.values())).variables
        return {}

    @property
    def header_variables(self) -> Dict[str, Header]:
        """Pass-through to first instance for compatibility."""
        if self.instances:
            return next(iter(self.instances.values())).header_variables
        return {}

    def get_all(self) -> Dict[Any, Header | Variable]:
        """Pass-through to first instance for compatibility."""
        if self.instances:
            return next(iter(self.instances.values())).get_all()
        return {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert _EventConfig to YAML-compatible dictionary."""
        return {
            instance_id: instance.to_dict()
            for instance_id, instance in self.instances.items()
        }


# Main-formats ********************************************************+
class EventsConfig(BaseModel):
    """Events configuration dict keyed by event_id."""
    events: Dict[Any, _EventConfig]

    @classmethod
    def _init(cls, events_dict: Dict[Any, Dict[str, Any]]) -> Self:
        new_dict = {}
        for event_id, instances in events_dict.items():
            new_dict[event_id] = _EventConfig._init(instances)
        return cls(events=new_dict)

    def __getitem__(self, idx: str | int) -> _EventConfig | None:
        if idx not in self.events:
            return None
        return self.events[idx]

    def __contains__(self, idx: str | int) -> bool:
        return idx in self.events

    def to_dict(self) -> Dict[Any, Any]:
        """Convert EventsConfig to YAML-compatible dictionary.

        This unwraps the internal 'events' dict structure to match YAML
        format.
        """
        result = {}
        for event_id, event_config in self.events.items():
            # Convert string keys back to int if they were originally int
            try:
                key = int(event_id)
            except (ValueError, TypeError):
                key = event_id
            result[key] = event_config.to_dict()
        return result
