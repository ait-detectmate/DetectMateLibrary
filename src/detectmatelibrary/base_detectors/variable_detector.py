from detectmatelibrary.common._config._compile import (
    generate_events_config,
    get_configured_variables,
    get_global_variables,
)
from detectmatelibrary.common.detector import _time_handler as _core_time_handler
from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.base_detectors.tracker_detector import (
    StabilityAutoConfigParams,
    TrackerDetector,
    TrackerDetectorConfig,
)

from detectmatelibrary.utils.persistency.data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.tools.logging import logger

from typing_extensions import override
from typing import Any, Dict, Optional, cast
from pydantic import Field


class VariableAutoConfigParams(StabilityAutoConfigParams):
    use_stable_vars: bool = Field(
        default=True, description="Monitor the variables the configure phase classifies as STABLE."
    )
    use_static_vars: bool = Field(
        default=True,
        description="Monitor the variables the configure phase classifies as STATIC (a single value).",
    )


class VariableDetectorConfig(TrackerDetectorConfig):
    auto_config_params: VariableAutoConfigParams = VariableAutoConfigParams()
    method_type: str = "variable_detector"


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


def add_variables(
    vars: Dict[Any, Any], tracker: EventStabilityTracker, auto: VariableAutoConfigParams, e_id: int | str
) -> None:
    stable = tracker.get_features_by_classification("STABLE") if auto.use_stable_vars else []
    static = tracker.get_features_by_classification("STATIC") if auto.use_static_vars else []
    selected = stable + static
    if selected:
        vars[e_id] = selected


def validate_config_coverage(
        detector_name: str,
        config_events: EventsConfig | dict[str, Any],
        event_persistency: EventPersistency,
) -> None:
    """Log warnings when configured EventIDs or variables have no training
    data.

    Args:
        detector_name: Name of the detector (used in warning messages).
        config_events: The detector's events configuration.
        event_persistency: The persistency object populated during training.
    """
    config_ids = (
        config_events.events.keys()
        if isinstance(config_events, EventsConfig)
        else config_events.keys()
    )
    if not config_ids:
        return

    events_seen = event_persistency.get_events_seen()
    events_with_data = set(event_persistency.get_events_data().keys())

    for event_id in config_ids:
        if event_id not in events_seen:
            logger.warning(
                f"[{detector_name}] EventID {event_id!r} is configured but was "
                "never observed in training data. Verify that EventIDs in your "
                "config match those produced by the parser."
            )
        elif event_id not in events_with_data:
            logger.warning(
                f"[{detector_name}] EventID {event_id!r} was observed in training "
                "data but no configured variables were extracted. Verify that "
                "variable names/positions in your config match those in the data."
            )


class VariableDetector(TrackerDetector):
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

    # Shared with CoreDetector's timestamp extraction, as before the move.
    _time_handler: TimeFormatHandler = _core_time_handler

    def __init__(
        self, name: str, config: VariableDetectorConfig = VariableDetectorConfig()
    ) -> None:
        if isinstance(config, dict):
            config = VariableDetectorConfig.from_dict(config, name)

        super().__init__(name=name, config=config, stability_params=config.auto_config_params)
        self.config: VariableDetectorConfig

    # ---- hooks --------------------------------------------------------------

    def _stability_kwargs(self) -> Dict[str, Any]:
        """Redfine to be specific to the detector."""
        name = type(self).__name__
        return {
            "add_value_fn": name,
            "detector_config": strip_auto_config_params(self.config.to_dict(method_id=name), name),
        }

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

    # ---- lifecycle ----------------------------------------------------------

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        variables = get_configured_variables(input_, self.config.events)
        self._ingest(input_, self._prepare_variables(variables, "training"), input_["EventID"])
        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                self._ingest(input_, self._prepare_variables(global_vars, "training"), GLOBAL_EVENT_ID)

    def detect(self, input_: ParserSchema, output_: DetectorSchema) -> bool:  # type: ignore
        alerts: Dict[str, str] = {}
        overall_score = 0.0
        known_events = self.persistency.get_events_data()
        current_event_id = input_["EventID"]

        if current_event_id in known_events:
            variables = self._prepare_variables(
                get_configured_variables(input_, self.config.events), "detection"
            )
            event_tracker = known_events[current_event_id]
            overall_score += self._check_event(
                alerts, current_event_id, event_tracker, variables, is_global=False
            )
        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = self._prepare_variables(
                get_global_variables(input_, self.config.global_instances), "detection"
            )
            global_tracker = known_events[GLOBAL_EVENT_ID]
            overall_score += self._check_event(
                alerts, GLOBAL_EVENT_ID, global_tracker, global_vars, is_global=True
            )

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = self._description()
            output_["alertsObtain"].update(alerts)
            return True
        return False

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            named_variables=input_["logFormatVariables"],
            timestamp=self._timestamp(input_),
        )

    @override
    def post_train(self) -> None:
        if not self.config.auto_config:
            validate_config_coverage(self.name, self.config.events, self.persistency)

    def set_configuration(self) -> None:
        variables: Dict[Any, Any] = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stability_tracker = tracker
            auto = self.config.auto_config_params
            add_variables(variables, tracker=stability_tracker, auto=auto, e_id=event_id)

        self.config.events = generate_events_config(variables, self.name)
        self.config.auto_config = False
        if not self.config.events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )
