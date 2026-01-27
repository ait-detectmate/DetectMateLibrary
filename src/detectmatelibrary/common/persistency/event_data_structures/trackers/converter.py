"""Converter classes for transforming input data in EventTracker."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class Converter(ABC):
    """Abstract base class for data converters."""

    @abstractmethod
    def convert(self, values_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw data into the format expected by the tracker."""
        pass


class InvariantConverter(Converter):
    """Converter that returns data unchanged."""

    def convert(self, values_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Return the input data unchanged."""
        return values_dict


class ComboConverter(Converter):
    """Converter for combo data."""

    def convert(self, values_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw combo data into the format expected by the tracker."""

        return values_dict
