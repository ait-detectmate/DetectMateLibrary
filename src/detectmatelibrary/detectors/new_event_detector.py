from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common.detector import CoreDetectorConfig, CoreDetector, get_configured_variables, \
    get_global_variables
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker
)
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.schemas import ParserSchema, DetectorSchema


class NewEventDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_event_detector"


class NewEventDetector(CoreDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self,
        name: str = "NewEventDetector",
        config: NewEventDetectorConfig = NewEventDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewEventDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: NewEventDetectorConfig
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"]
        )
        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                self.persistency.ingest_event(
                    event_id=GLOBAL_EVENT_ID,
                    event_template=input_["template"]
                )

    def detect(
        self, input_:  ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        """Detect new values in the input data."""
        alerts: dict[str, str] = {}
        overall_score = 0.0

        current_event_id = input_["EventID"]
        known_events = self.persistency.get_events_seen()

        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = get_global_variables(input_, self.config.global_instances)
            alerts[f"Global - {global_vars}"] = f"Unknown event ID: '{current_event_id}'"
            overall_score += 1.0
        elif current_event_id not in known_events:
            configured_variables = get_configured_variables(input_, self.config.events)
            alerts[f"EventID {current_event_id} - {configured_variables}"] = (
                f"Unknown event ID: '{current_event_id}'"
            )
            overall_score += 1.0

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = \
                f"{self.name} detects event IDs not encountered in training as anomalies."
            output_["alertsObtain"].update(alerts)
            return True

        return False

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"]
        )

    def set_configuration(self) -> None:
        config_dict = generate_detector_config(
            variable_selection={},
            detector_name=self.name,
            method_type=self.config.method_type
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewEventDetectorConfig.from_dict(config_dict, self.name)
