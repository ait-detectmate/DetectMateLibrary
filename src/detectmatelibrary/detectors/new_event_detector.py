from detectmatelibrary.common._config._compile import generate_events_config
from detectmatelibrary.common.detector import CoreDetectorConfig, CoreDetector
from detectmatelibrary.common.variable_detector import get_global_variables
from detectmatelibrary.utils import persistency
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.common._config._compile import (
    get_configured_variables
)


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
        self.persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker
        )
        self._register_persistency(self.persistency)

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
        # This detector keys on EventIDs only -- it selects no variables, so
        # the configure phase produces an empty events block.
        self.config.events = generate_events_config({}, self.name)
        self.config.auto_config = False
