from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
)

from typing import Any, Dict, Optional, cast


class VariableHooks:
    """The hooks a ``VariableDetector`` subclass overrides:

      - ``_check_variable`` (required): the per-variable anomaly test.
      - ``_prepare_variables`` (optional): transform variables per stage.
      - ``_check_event`` (optional): score one event's variables.
      - ``_description`` / ``_alert_key`` (optional): output formatting.

    ``VariableDetector``'s lifecycle calls these; they do not depend on it.
    """

    name: str

    def _prepare_variables(self, variables: Dict[str, Any], stage: str) -> Dict[str, Any]:
        """Transform extracted variables.

        ``stage`` is "training" or "detection".
        """
        return variables

    def _check_variable(
        self, tracker: SingleStabilityTracker, value: Any, key: Any
    ) -> Optional[str]:
        """Return an alert message if ``value`` is anomalous for ``tracker``,
        else None."""
        raise NotImplementedError

    def _alert_key(self, event_id: Any, key: Any, is_global: bool) -> str:
        return f"Global - {key}" if is_global else f"EventID {event_id} - {key}"

    def _description(self) -> str:
        return f"{self.name} detected anomalies."

    def _check_event(
        self,
        alerts: Dict[str, str],
        event_id: Any,
        event_tracker: EventStabilityTracker,
        variables: Dict[str, Any],
        is_global: bool,
    ) -> float:
        """Loop the event's per-variable trackers, accumulate alerts, score +1
        per anomalous variable."""
        score = 0.0
        var_trackers = cast(Dict[str, SingleStabilityTracker], event_tracker.get_data())
        for key, tracker in var_trackers.items():
            value = variables.get(key)
            if value is None:
                continue
            message = self._check_variable(tracker, value, key)
            if message:
                alerts[self._alert_key(event_id, key, is_global)] = message
                score += 1.0
        return score
