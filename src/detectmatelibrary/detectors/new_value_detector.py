from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig

from detectmatelibrary.common.detector import (
    CoreDetectorConfig,
    CoreDetector,
    get_configured_variables,
    get_global_variables,
    validate_config_coverage,
)
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID

from typing_extensions import override
from tools.logging import logger


class NewValueDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_detector"

    use_stable_vars: bool = True
    use_static_vars: bool = True


class NewValueDetector(CoreDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self,
        name: str = "NewValueDetector",
        config: NewValueDetectorConfig = NewValueDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewValueDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: NewValueDetectorConfig  # type narrowing for IDE
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )
        self._register_persistency(self.persistency)

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        configured_variables = get_configured_variables(input_, self.config.events)
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            named_variables=configured_variables
        )
        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                self.persistency.ingest_event(
                    event_id=GLOBAL_EVENT_ID,
                    event_template=input_["template"],
                    named_variables=global_vars
                )

    def detect(
        self, input_:  ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        """Detect new values in the input data."""
        alerts: dict[str, str] = {}
        configured_variables = get_configured_variables(input_, self.config.events)
        overall_score = 0.0

        current_event_id = input_["EventID"]
        known_events = self.persistency.get_events_data()

        if current_event_id in known_events:
            event_tracker = known_events[current_event_id]
            for var_name, multi_tracker in event_tracker.get_data().items():
                value = configured_variables.get(var_name)
                if value is None:
                    continue
                if value not in multi_tracker.unique_set:
                    alerts[f"EventID {current_event_id} - {var_name}"] = (
                        f"Unknown value: '{value}'"
                    )
                    overall_score += 1.0

        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = get_global_variables(input_, self.config.global_instances)
            global_tracker = known_events[GLOBAL_EVENT_ID]
            for var_name, multi_tracker in global_tracker.get_data().items():
                value = global_vars.get(var_name)
                if value is None:
                    continue
                if value not in multi_tracker.unique_set:
                    alerts[f"Global - {var_name}"] = f"Unknown value: '{value}'"
                    overall_score += 1.0

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = f"{self.name} detects values not encountered in training as anomalies."
            output_["alertsObtain"].update(alerts)
            return True

        return False

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
        variables = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable = []
            if self.config.use_stable_vars:
                stable = tracker.get_features_by_classification("STABLE")  # type: ignore
            static = []
            if self.config.use_static_vars:
                static = tracker.get_features_by_classification("STATIC")  # type: ignore
            vars_ = stable + static
            if len(vars_) > 0:
                variables[event_id] = vars_
        old_persist = self.config.persist
        config_dict = generate_detector_config(
            variable_selection=variables,
            detector_name=self.name,
            method_type=self.config.method_type,
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewValueDetectorConfig.from_dict(config_dict, self.name)
        self.config.persist = old_persist
        events = self.config.events
        if isinstance(events, EventsConfig) and not events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )
