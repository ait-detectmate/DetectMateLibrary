from typing import Any, Dict, Optional

from detectmatelibrary.common.variable_detector import VariableDetector, VariableDetectorConfig
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)
from detectmatelibrary.tools.logging import logger


class ValueRangeDetectorConfig(VariableDetectorConfig):
    method_type: str = "value_range_detector"

    ignore_non_numerical_val: bool = True


class ValueRangeDetector(VariableDetector):
    """Detect out-of-range numeric values in logs based on learned min/max."""

    def __init__(
        self,
        name: str = "ValueRangeDetector",
        config: ValueRangeDetectorConfig = ValueRangeDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = ValueRangeDetectorConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self.config: ValueRangeDetectorConfig  # type narrowing for IDE

    def cast_val_to_numeric(self, configured_variables: Dict[str, Any], k: str, remove: List[str],
                            stage: str) -> bool:
        # Detection iterates over vars learned in training; a var can be absent from the
        # current line for variable-length events (get_configured_variables skips positions
        # beyond the line's variable count). Skip it — caller already handles `not cast`.
        if k not in configured_variables:
            return False
        v = configured_variables[k]
        if not isinstance(v, (int, float)):
          
    def add_value(self, tracker: SingleStabilityTracker, value: Any) -> None:
        """Add a new value to the tracker (range semantics)."""
        try:
            value = float(value)
            value = int(value) if value.is_integer() else value
        except ValueError:
            return
        if len(tracker.unique_set) > 0:
            min_ = min(tracker.unique_set)
            max_ = max(tracker.unique_set)
            tracker.change_series.append(value < min_ or value > max_)
        else:
            tracker.change_series.append(True)
        tracker.unique_set.add(value)

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return self._stability_kwargs()

    def _prepare_variables(self, variables: Dict[str, Any], stage: str) -> Dict[str, Any]:
        """Cast values to numeric; drop (or exit on) non-numeric ones."""
        remove = []
        for key in list(variables.keys()):
            v = variables[key]
            if isinstance(v, (int, float)):
                continue
            try:
                casted = float(v)
                variables[key] = int(casted) if casted.is_integer() else casted
            except ValueError:
                msg = (
                    f"Non-numeric value '{v}' appeared in {stage} of {type(self).__name__}"
                    f" with the name {self.name}."
                )
                if not self.config.ignore_non_numerical_val:
                    raise ValueError(msg)
                logger.error(msg)
                remove.append(key)
        for key in remove:
            del variables[key]
        return variables

    def _check_variable(
        self, tracker: SingleStabilityTracker, value: Any, key: Any
    ) -> Optional[str]:
        min_ = min(tracker.unique_set)
        max_ = max(tracker.unique_set)
        if value < min_ or value > max_:
            return f"Out of range value: '{value}' ({min_} - {max_})"
        return None

    def _description(self) -> str:
        return f"{self.name} detects values not encountered in training as anomalies."
