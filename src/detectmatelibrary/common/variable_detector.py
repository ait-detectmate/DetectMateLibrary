from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
)
from detectmatelibrary.utils.persistency.component_interfaces import (
    validate_config_coverage
)
from detectmatelibrary.utils.data_buffer import BufferMode


from detectmatelibrary.common._config._compile import (
    generate_events_config,
    get_configured_variables,
)
from detectmatelibrary.common._other_op._variable_hooks import (
    get_global_variables, strip_auto_config_params, VariableAutoConfigParams, VariablesLogic

)
from detectmatelibrary.common.detector import (
    CoreDetectorConfig,
    CoreDetector,
    _time_handler
)

from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.tools.logging import logger

from typing_extensions import override
from typing import Any, Dict, cast


class VariableDetectorConfig(CoreDetectorConfig):
    auto_config_params: VariableAutoConfigParams = VariableAutoConfigParams()


def add_variables(
    vars: Dict[Any, Any], tracker: EventStabilityTracker, auto: VariableAutoConfigParams, e_id: int | str
) -> None:
    stable = tracker.get_features_by_classification("STABLE") if auto.use_stable_vars else []
    static = tracker.get_features_by_classification("STATIC") if auto.use_static_vars else []
    selected = stable + static
    if selected:
        vars[e_id] = selected


class VariableDetector(CoreDetector, VariablesLogic):
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
        CoreDetector.__init__(self, name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: VariableDetectorConfig
        VariablesLogic.__init__(
            self, name=self.name, _time_handler=_time_handler, config_vars=self.config.auto_config_params
        )
        self._register_persistency(self.persistency)

    def _stability_kwargs(self) -> Dict[str, Any]:
        """Redfine to be specific to the detector."""
        name = type(self).__name__
        return {
            "add_value_fn": name,
            "detector_config": strip_auto_config_params(self.config.to_dict(method_id=name), name),
        }

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        self._ingest(input_, get_configured_variables(input_, self.config.events), input_["EventID"])
        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                self._ingest(input_, global_vars, GLOBAL_EVENT_ID)

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
            add_variables(variables, tracker=stability_tracker, auto=auto, e_id=event_id)

        self.config.events = generate_events_config(variables, self.name)
        self.config.auto_config = False
        if not self.config.events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )

    def aggregate_strategy(self, components: set["VariableDetector"]) -> None:  # type: ignore
        self.combine(components)  # type: ignore
