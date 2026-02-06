from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.common.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker
)
from detectmatelibrary.common.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing import Any


class NewValueDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_detector"

    events: EventsConfig | dict[str, Any] = {}


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

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        configured_variables = self.get_configured_variables(input_, self.config.events)
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            named_variables=configured_variables
        )

    def detect(
        self, input_:  ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        """Detect new values in the input data."""
        alerts: dict[str, str] = {}

        configured_variables = self.get_configured_variables(input_, self.config.events)

        overall_score = 0.0

        for event_id, event_tracker in self.persistency.get_events_data().items():
            for event_id, multi_tracker in event_tracker.get_data().items():
                value = configured_variables.get(event_id)
                if value is None:
                    continue
                if value not in multi_tracker.unique_set:
                    alerts[f"EventID {event_id}"] = (
                        f"Unknown value: '{value}'"
                    )
                    overall_score += 1.0

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = f"{self.name} detects values not encountered in training as anomalies."
            output_["alertsObtain"].update(alerts)
            return True

        return False

    def configure(self, input_: ParserSchema) -> None:
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            named_variables=input_["logFormatVariables"],
        )

    def set_configuration(self) -> None:
        variables = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_variables_by_classification("STABLE")  # type: ignore
            variables[event_id] = stable_vars
        config_dict = generate_detector_config(
            variable_selection=variables,
            detector_name=self.name,
            method_type=self.config.method_type,
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewValueDetectorConfig.from_dict(config_dict, self.name)
