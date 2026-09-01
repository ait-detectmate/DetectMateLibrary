from detectmatelibrary.common._config._formats import _EventInstance
from detectmatelibrary.common._config._compile import (
    generate_events_config,
    get_configured_variables,
)
from detectmatelibrary.common.detector import (
    AutoConfigParams,
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
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability import (
    ClassificationMethods,
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler
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


def _strip_auto_config_params(detector_config: Dict[str, Any], method_id: str) -> Dict[str, Any]:
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
    """Configure-phase inputs shared by every VariableDetector subclass.

    Read only while `auto_config` is True: stability classification decides
    which variables land in the generated `events` block and is never consulted
    at detection time.
    """

    use_stable_vars: bool = True
    use_static_vars: bool = True

    # Which stability classification methods decide STABLE, and how their
    # verdicts combine. Four independent methods over two primitives and two
    # axes; see ClassificationMethods. The two time-axis methods (`time`,
    # `slope_time`) need a per-record event time, named here and read from the
    # record's logFormatVariables.
    classification: ClassificationMethods = ClassificationMethods()
    timestamp_variable: str | None = None
    timestamp_format: str | None = None  # None -> TimeFormatHandler auto-detect


class VariableDetectorConfig(CoreDetectorConfig):
    auto_config_params: VariableAutoConfigParams = VariableAutoConfigParams()


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
        self._time_handler = TimeFormatHandler()
        self._warned_bad_timestamp = False
        self.persistency = EventPersistency(
            event_data_class=self._event_data_class(),
            # No classification kwargs: the trained trackers are read by
            # _check_variable, which looks at unique_set / min-max / charset
            # directly and never calls classify(). A classification block
            # would only make them collect timestamps nothing reads.
            event_data_kwargs=self._event_data_kwargs(),
        )
        # auto config checks individual-variable stability to select features
        self.auto_conf_persistency = EventPersistency(
            event_data_class=self._event_data_class(),
            event_data_kwargs=self._with_classification_kwargs(self._auto_conf_kwargs()),
        )
        self._register_persistency(self.persistency)

    def _with_classification_kwargs(
        self, kwargs: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Add the classification block to tracker kwargs, unless it is the
        default.

        Done here rather than in _stability_kwargs so every VariableDetector
        subclass is covered -- NewValueDetector overrides neither construction
        hook and NewValueComboDetector returns only a converter_function.

        Non-defaults only: forwarding the default block would be noise, and a
        block naming a time-axis method would make every variable collect
        timestamps it never reads.
        """
        auto = self.config.auto_config_params
        if auto.classification == ClassificationMethods():
            return kwargs
        return {**(kwargs or {}), "classification": auto.classification.model_dump()}

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
            "detector_config": _strip_auto_config_params(self.config.to_dict(method_id=name), name),
        }

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
        auto = self.config.auto_config_params
        if not auto.classification.needs_timestamps:
            return None
        if not auto.timestamp_variable:
            # Selecting a time-axis method without naming the field is an
            # operator error, not an opt-out -- say so rather than silently
            # no-op.
            self._warn_time_fallback_once(
                "a time-axis classification method is enabled "
                "but timestamp_variable is not set"
            )
            return None
        raw = input_["logFormatVariables"].get(auto.timestamp_variable)
        ts = self._time_handler.parse_timestamp(str(raw or ""), auto.timestamp_format)
        if ts == "0":
            self._warn_time_fallback_once(
                f"timestamp_variable {auto.timestamp_variable!r} is missing or "
                f"unparseable (got {raw!r})"
            )
            return None
        return float(ts)

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
            timestamp=self._timestamp(input_),
        )

    @override
    def post_train(self) -> None:
        if not self.config.auto_config:
            validate_config_coverage(self.name, self.config.events, self.persistency)

    def set_configuration(self) -> None:
        variables: Dict[Any, Any] = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stability_tracker = cast(EventStabilityTracker, tracker)
            auto = self.config.auto_config_params
            stable = (
                stability_tracker.get_features_by_classification("STABLE")
                if auto.use_stable_vars
                else []
            )
            static = (
                stability_tracker.get_features_by_classification("STATIC")
                if auto.use_static_vars
                else []
            )
            selected = stable + static
            if selected:
                variables[event_id] = selected
        # Write only what the configure phase produced. Rebuilding the config
        # from generate_detector_config is what used to drop operator settings:
        # it emits four keys, so everything else had to be carried across by
        # hand and a forgotten field failed silently.
        self.config.events = generate_events_config(variables, self.name)
        self.config.auto_config = False
        if not self.config.events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )
