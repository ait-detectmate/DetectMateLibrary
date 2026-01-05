from abc import ABC, abstractmethod
from typing import Any, List


class EventDataStructure(ABC):
    """Storage backend interface for event-based data analysis."""

    @abstractmethod
    def add_data(self, data_object: Any) -> None: ...

    @abstractmethod
    def get_data(self) -> Any: ...

    @abstractmethod
    def get_variables(self) -> List[str]: ...

    @classmethod
    @abstractmethod
    def to_data(cls, raw_data: Any) -> Any: ...
