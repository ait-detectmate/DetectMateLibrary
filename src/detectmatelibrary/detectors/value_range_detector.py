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


class ValueRangeDetectorConfig(CoreDetectorConfig):
    method_type: str = "value_range_detector"

    use_stable_vars: bool = True
    use_static_vars: bool = True


class ValueRangeDetector(CoreDetector):
    """Detect new value ranges in logs as anomalies based on learned values."""

    def __init__(
        self,
        name: str = "ValueRangeDetector",
        config: ValueRangeDetectorConfig = ValueRangeDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = ValueRangeDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: ValueRangeDetectorConfig  # type narrowing for IDE
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )

    def cast_val_to_numeric(self, configured_variables, k, remove):
        v = configured_variables[k]
        if not isinstance(v, (int, float)):
            try:
                configured_variables[k] = int(v)
            except ValueError:
                try:
                    configured_variables[k] = float(v)
                except ValueError:
                    logger.error(f"Non-numeric value '{v}' appeared in training of {self.__class__.__name__}"
                                 f" with the name {self.name}.")
                    exit(1)
                    # TODO: what to do in this case; exit the program or skipping the data?
                    remove.append(k)

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        configured_variables = get_configured_variables(input_, self.config.events)
        remove = []
        for k in configured_variables.keys():
            self.cast_val_to_numeric(configured_variables, k, remove)
        for k in remove:
            del configured_variables[k]
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
        """Detect new value ranges in the input data."""
        alerts: dict[str, str] = {}
        configured_variables = get_configured_variables(input_, self.config.events)
        #print("configured", configured_variables)
        #print("input", input_)
        overall_score = 0.0

        current_event_id = input_["EventID"]
        known_events = self.persistency.get_events_data()
        print("KNOWN EVENTS", known_events)

        if current_event_id in known_events:
            event_tracker = known_events[current_event_id]
            for var_name, multi_tracker in event_tracker.get_data().items():
                self.cast_val_to_numeric(configured_variables, var_name, [])
                value = configured_variables.get(var_name)
                if value is None:
                    continue
                min_ = min(multi_tracker.unique_set)
                max_ = max(multi_tracker.unique_set)
                if value < min_ or value > max_:
                    alerts[f"EventID {current_event_id} - {var_name}"] = (
                        f"Out of range value: '{value}' ({min_} - {max_})"
                    )
                    overall_score += 1.0

        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = get_global_variables(input_, self.config.global_instances)
            global_tracker = known_events[GLOBAL_EVENT_ID]
            for var_name, multi_tracker in global_tracker.get_data().items():
                self.cast_val_to_numeric(global_vars, var_name, [])
                value = global_vars.get(var_name)
                if value is None:
                    continue
                min_ = min(multi_tracker.unique_set)
                max_ = max(multi_tracker.unique_set)
                if value < min_ or value > max_:
                    alerts[f"Global - {var_name}"] = f"Unknown value: '{value}'"
                    overall_score += 1.0

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = f"{self.name} detects values not encountered in training as anomalies."
            output_["alertsObtain"].update(alerts)
            return True

        return False

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        print(input_["variables"], "AAA")
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
            # UNSTABLE VARS ARE POSSIBLE HERE!
            stable = []
            if self.config.use_stable_vars:
                stable = tracker.get_features_by_classification("STABLE")  # type: ignore
            static = []
            if self.config.use_static_vars:
                static = tracker.get_features_by_classification("STATIC")  # type: ignore
            vars_ = stable + static
            if len(vars_) > 0:
                variables[event_id] = vars_
        config_dict = generate_detector_config(
            variable_selection=variables,
            detector_name=self.name,
            method_type=self.config.method_type,
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = ValueRangeDetectorConfig.from_dict(config_dict, self.name)
        events = self.config.events
        if isinstance(events, EventsConfig) and not events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )
