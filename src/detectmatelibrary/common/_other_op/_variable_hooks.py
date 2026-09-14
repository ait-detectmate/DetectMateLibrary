from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability import ClassificationMethods
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
     EventStabilityTracker, SingleStabilityTracker
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

from detectmatelibrary.common._config._formats import _EventInstance
from detectmatelibrary.common.detector import AutoConfigParams


from detectmatelibrary.tools.logging import logger
from detectmatelibrary.schemas import ParserSchema

from typing import Any, Dict, Optional, cast


def get_global_variables(
        input_: ParserSchema,
        global_instances: Dict[str, _EventInstance],
) -> Dict[str, Any]:
    """Extract header variables from event-ID-independent instances.

    Args:
        input_: Parser schema containing logFormatVariables
        global_instances: Dict of instance_name -> _EventInstance configs

    Returns:
        Dict mapping variable names to their values from the input
    """
    result: Dict[str, Any] = {}
    for instance in global_instances.values():
        for name in instance.header_variables:
            if name in input_["logFormatVariables"]:
                result[name] = input_["logFormatVariables"][name]
    return result


def strip_auto_config_params(detector_config: Dict[str, Any], method_id: str) -> Dict[str, Any]:
    """Return a copy of a serialized detector_config with its
    auto_config_params block removed.

    detector_config is stashed on a tracker and persisted verbatim by
    to_state(). auto_config_params are configure-phase-only inputs --
    the standing constraint is that persisted tracker state never
    carries them. Stripped here, at the point the kwargs are built, so
    the block never reaches state in the first place.
    """
    entry = detector_config.get("detectors", {}).get(method_id, {})
    if "auto_config_params" not in entry:
        return detector_config
    return {
        **detector_config,
        "detectors": {
            **detector_config["detectors"],
            method_id: {k: v for k, v in entry.items() if k != "auto_config_params"},
        },
    }


class VariableAutoConfigParams(AutoConfigParams):
    use_stable_vars: bool = True
    use_static_vars: bool = True
    classification: ClassificationMethods = ClassificationMethods()
    timestamp_variable: str | None = None
    timestamp_format: str | None = None  # None -> TimeFormatHandler auto-detect


class VaribaleHooks:
    """Hooks use to define the dfferent behaviours in th next subclasses."""
    def __init__(self, name: str, config_vars: VariableAutoConfigParams) -> None:
        self.name = name
        self._warned_bad_timestamp: bool = False
        self.config_vars = config_vars

    def _with_classification_kwargs(
        self, kwargs: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:

        if self.config_vars.classification == ClassificationMethods():
            return kwargs
        return {**(kwargs or {}), "classification": self.config_vars.classification.model_dump()}

    def _event_data_class(self) -> type:
        return EventStabilityTracker

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return None

    def _auto_conf_kwargs(self) -> Optional[Dict[str, Any]]:
        return self._event_data_kwargs()

    def _stability_kwargs(self) -> Dict[str, Any]:
        return {}

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


class VariablesLogic(VaribaleHooks):
    """Variables logic combining the hooks and persistency class."""
    def __init__(
        self,
        name: str,
        _time_handler: TimeFormatHandler = TimeFormatHandler(),
        config_vars: VariableAutoConfigParams = VariableAutoConfigParams(),
    ) -> None:

        super().__init__(name=name, config_vars=config_vars)
        self._time_handler = _time_handler
        self.persistency = EventPersistency(
            event_data_class=self._event_data_class(),
            event_data_kwargs=self._event_data_kwargs(),
        )
        self.auto_conf_persistency = EventPersistency(
            event_data_class=self._event_data_class(),
            event_data_kwargs=self._with_classification_kwargs(self._auto_conf_kwargs()),
        )

    def _warn_time_fallback_once(self, reason: str) -> None:
        """Log the first time-dependent misconfiguration, then stay quiet.

        A bad config would otherwise emit one warning per record, so the
        flag latches after the first message.
        """
        if self._warned_bad_timestamp:
            return
        self._warned_bad_timestamp = True
        logger.warning(
            "%s: %s; falling back to the index axis for stability classification.",
            self.name, reason,
        )

    def _timestamp(self, input_: ParserSchema) -> float | None:
        """Resolve the record's event time, or None if no enabled
        classification method reads the time axis."""
        if not self.config_vars.classification.needs_timestamps:
            return None

        if not self.config_vars.timestamp_variable:
            self._warn_time_fallback_once(
                "a time-axis classification method is enabled "
                "but timestamp_variable is not set"
            )
            return None

        raw = input_["logFormatVariables"].get(self.config_vars.timestamp_variable)
        ts = self._time_handler.parse_timestamp(str(raw or ""), self.config_vars.timestamp_format)
        if ts == "0":
            self._warn_time_fallback_once(
                f"timestamp_variable {self.config_vars.timestamp_variable!r} is missing or "
                f"unparseable (got {raw!r})"
            )
            return None

        return float(ts)

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

    def _ingest(self, input_: ParserSchema, variables: Dict[str, Any], event_id: Any) -> None:
        variables = self._prepare_variables(variables, "training")
        self.persistency.ingest_event(
            event_id=event_id,
            event_template=input_["template"],
            named_variables=variables,
        )
