from detectmatelibrary.common.variable_detector import VariableDetector, VariableDetectorConfig
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)

from typing import Any, Dict, Optional


class CharsetDetectorConfig(VariableDetectorConfig):
    method_type: str = "charset_detector"


class CharsetDetector(VariableDetector):
    """Detect characters in log data not seen in training as anomalies."""

    def __init__(
        self,
        name: str = "CharsetDetector",
        config: CharsetDetectorConfig = CharsetDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CharsetDetectorConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self.config: CharsetDetectorConfig  # type narrowing for IDE

    def add_value(self, tracker: SingleStabilityTracker, value: Any) -> None:
        """Add a new value to the tracker (character-set semantics)."""
        before = len(tracker.unique_set)
        tracker.unique_set.update(value)
        tracker.change_series.append(len(tracker.unique_set) > before)

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return self._stability_kwargs()

    def _check_variable(
        self, tracker: SingleStabilityTracker, value: Any, key: Any
    ) -> Optional[str]:
        unknown = set(value) - tracker.unique_set
        if unknown:
            return "Unknown character(s): " + ", ".join(f"'{c}'" for c in sorted(unknown))
        return None

    def _description(self) -> str:
        return f"{self.name} detects characters not encountered in training as anomalies."
