from detectmatelibrary.common.variable_detector import VariableDetector, VariableDetectorConfig
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)

from typing import Any, Optional


class NewValueDetectorConfig(VariableDetectorConfig):
    method_type: str = "new_value_detector"


class NewValueDetector(VariableDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self,
        name: str = "NewValueDetector",
        config: NewValueDetectorConfig = NewValueDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = NewValueDetectorConfig.from_dict(config, name)
        super().__init__(name=name, config=config)
        self.config: NewValueDetectorConfig  # type narrowing for IDE

    def _check_variable(
        self, tracker: SingleStabilityTracker, value: Any, key: Any
    ) -> Optional[str]:
        if value not in tracker.unique_set:
            return f"Unknown value: '{value}'"
        return None

    def _description(self) -> str:
        return f"{self.name} detects values not encountered in training as anomalies."
