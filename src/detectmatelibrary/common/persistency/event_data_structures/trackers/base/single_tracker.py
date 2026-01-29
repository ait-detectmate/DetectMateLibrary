"""Tracks whether a variable is converging to a constant value."""

from typing import Any
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class Classification:
    type: str = ""
    reason: str = ""


class SingleTracker(ABC):
    """Tracks whether a single variable is converging to a constant value."""

    @abstractmethod
    def add_value(self, value: Any) -> None:
        """Add a new value to the tracker."""

    @abstractmethod
    def classify(self) -> Classification:
        """Classify the tracker based on the current data."""
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass
