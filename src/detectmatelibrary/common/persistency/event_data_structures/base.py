from abc import ABC, abstractmethod
from typing import Any, List
from dataclasses import dataclass


@dataclass
class EventDataStructure(ABC):
    """Storage backend interface for event-based data analysis."""

    event_id: int = -1
    template: str = ""

    @abstractmethod
    def add_data(self, data_object: Any) -> None: ...

    @abstractmethod
    def get_data(self) -> Any: ...

    @abstractmethod
    def get_variables(self) -> List[str]: ...

    @classmethod
    @abstractmethod
    def to_data(cls, raw_data: Any) -> Any:
        """Convert raw data into the appropriate data format for storage."""
        pass

    def get_template(self) -> str:
        return self.template

    def get_event_id(self) -> int:
        return self.event_id
