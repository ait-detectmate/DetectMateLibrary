from abc import ABC, abstractmethod
from typing import Any, List
from dataclasses import dataclass


@dataclass
class EventDataStructure(ABC):
    """Storage backend interface for event-based data analysis."""

    event_id: int = -1
    template: str = ""

    @abstractmethod
    def _add_data(self, data_object: Any, timestamp: float | None = None) -> None: ...

    def add_data(
        self, data_object: Any, timestamp: float | None = None, do_preprocess: bool = False
    ) -> None:
        self._add_data(
            self.to_data(data_object) if do_preprocess else data_object,
            timestamp=timestamp
        )

    @abstractmethod
    def get_data(self) -> Any: ...

    @abstractmethod
    def get_variables(self) -> List[str]: ...

    @abstractmethod
    def to_data(self, raw_data: Any) -> Any:
        """Convert raw data into the appropriate data format for storage."""
        pass

    def as_dict(self) -> list[dict[int | str, Any]]:
        return []

    @abstractmethod
    def dump(self) -> bytes:
        """Serialize full state to bytes.

        Format is backend-specific.
        """
        ...

    @classmethod
    @abstractmethod
    def load(cls, data: bytes, **kwargs: Any) -> "EventDataStructure":
        """Restore state from bytes produced by dump()."""
        ...

    def get_template(self) -> str:
        return self.template

    def get_event_id(self) -> int:
        return self.event_id
