from detectmatelibrary.common._config._formats import _EventInstance, EventsConfig
from detectmatelibrary.common._config._compile import generate_detector_config, get_configured_variables
from detectmatelibrary.common.detector import (
    CoreDetectorConfig,
    CoreDetector,
)
from detectmatelibrary.utils.persistency.component_interfaces import (
    validate_config_coverage
)
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.tools.logging import logger

from typing import Any, Dict, Optional, cast
from typing_extensions import override


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


class VariableDetectorConfig(CoreDetectorConfig):
    use_stable_vars: bool = True
    use_static_vars: bool = True


class VariableDetector(CoreDetector):
    """Abstract base for detectors that learn a per-variable model from
    configured log variables and flag anomalous values at detection time.

    Subclasses override a small set of hooks:
      - ``_check_variable`` (required): the per-variable anomaly test.
      - ``_prepare_variables`` (optional): transform variables per stage.
      - ``_event_data_kwargs`` / ``_auto_conf_kwargs`` (optional): tracker
        construction kwargs.
      - ``_description`` / ``_alert_key`` (optional): output formatting.

    The five lifecycle methods (train/detect/configure/post_train/
    set_configuration) live here and are shared by all subclasses.
    """

    def __init__(self, name: str, config: VariableDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: VariableDetectorConfig  # type narrowing for IDE
        self.persistency = EventPersistency(
            event_data_class=self._event_data_class(),
            event_data_kwargs=self._event_data_kwargs(),
        )
        # auto config checks individual-variable stability to select features
        self.auto_conf_persistency = EventPersistency(
            event_data_class=self._event_data_class(),
            event_data_kwargs=self._auto_conf_kwargs(),
        )
        self._register_persistency(self.persistency)

    # ---- construction hooks -------------------------------------------------

    def _event_data_class(self) -> type:
        return EventStabilityTracker

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return None

    def _auto_conf_kwargs(self) -> Optional[Dict[str, Any]]:
        return self._event_data_kwargs()

    def _stability_kwargs(self) -> Dict[str, Any]:
        """Kwargs for detectors whose tracker rebinds a per-detector
        ``add_value`` closure (charset / value_range / bigram)."""
        name = type(self).__name__
        return {
            "add_value_fn": name,
            "detector_config": self.config.to_dict(method_id=name),
        }

    # ---- per-detector hooks -------------------------------------------------

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

    # ---- shared lifecycle ---------------------------------------------------

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        self._ingest(input_, get_configured_variables(input_, self.config.events), input_["EventID"])
        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                self._ingest(input_, global_vars, GLOBAL_EVENT_ID)

    def _ingest(self, input_: ParserSchema, variables: Dict[str, Any], event_id: Any) -> None:
        variables = self._prepare_variables(variables, "training")
        self.persistency.ingest_event(
            event_id=event_id,
            event_template=input_["template"],
            named_variables=variables,
        )

    def detect(self, input_: ParserSchema, output_: DetectorSchema) -> bool:  # type: ignore
        alerts: Dict[str, str] = {}
        overall_score = 0.0
        known_events = self.persistency.get_events_data()
        current_event_id = input_["EventID"]

        if current_event_id in known_events:
            variables = self._prepare_variables(
                get_configured_variables(input_, self.config.events), "detection"
            )
            event_tracker = cast(EventStabilityTracker, known_events[current_event_id])
            overall_score += self._check_event(
                alerts, current_event_id, event_tracker, variables, is_global=False
            )
        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = self._prepare_variables(
                get_global_variables(input_, self.config.global_instances), "detection"
            )
            global_tracker = cast(EventStabilityTracker, known_events[GLOBAL_EVENT_ID])
            overall_score += self._check_event(
                alerts, GLOBAL_EVENT_ID, global_tracker, global_vars, is_global=True
            )

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = self._description()
            output_["alertsObtain"].update(alerts)
            return True
        return False

    def _check_event(
        self,
        alerts: Dict[str, str],
        event_id: Any,
        event_tracker: EventStabilityTracker,
        variables: Dict[str, Any],
        is_global: bool,
    ) -> float:
        """Loop the event's per-variable trackers, accumulate alerts, score +1
        per anomalous variable.

        Bigram overrides this for event-level scoring.
        """
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

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            named_variables=input_["logFormatVariables"],
        )

    @override
    def post_train(self) -> None:
        if not self.config.auto_config:
            validate_config_coverage(self.name, self.config.events, self.persistency)

    def set_configuration(self) -> None:
        variables: Dict[Any, Any] = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stability_tracker = cast(EventStabilityTracker, tracker)
            stable = (
                stability_tracker.get_features_by_classification("STABLE")
                if self.config.use_stable_vars
                else []
            )
            static = (
                stability_tracker.get_features_by_classification("STATIC")
                if self.config.use_static_vars
                else []
            )
            selected = stable + static
            if selected:
                variables[event_id] = selected
        old_persist = self.config.persist
        config_dict = generate_detector_config(
            variable_selection=variables,
            detector_name=self.name,
            method_type=self.config.method_type,
        )
        self.config = type(self.config).from_dict(config_dict, self.name)
        self.config.persist = old_persist
        events = self.config.events
        if isinstance(events, EventsConfig) and not events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )
