from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig

from detectmatelibrary.common.detector import CoreDetectorConfig, CoreDetector, get_configured_variables

from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing import Any


class NewEventDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_event_detector"

    events: EventsConfig | dict[str, Any] = {}


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
        self.config: NewEventDetectorConfig  # type narrowing for IDE
        #print(self.config, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        configured_variables = get_configured_variables(input_, self.config.events)
        #print("AAAAAAAAAAAAAAAAA", input_, "BBBBBBBBBBBBB\n", self.config.events)
        #print(self.config.events)
        #print(input_["logFormatVariables"]["Type"], self.config.events)
        d = self.config.events[input_["EventID"]]
        #print("bbb", d)
        #print("ccc", hasattr(d, "header_variables"), d.header_variables.keys())
        #print("ccc", configured_variables)
        configured_variables = {k: v for k, v in configured_variables.items() if k in d.header_variables}
        print("conf", configured_variables)
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
        configured_variables = get_configured_variables(input_, self.config.events)
        #print("br", configured_variables)
        overall_score = 0.0

        current_event_id = input_["EventID"]
        known_events = self.persistency.get_events_data()
        #print(input_["logFormatVariables"]["Type"])
        #print(current_event_id, input_)

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

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = f"{self.name} detects values not encountered in training as anomalies."
            output_["alertsObtain"].update(alerts)
            return True

        return False

    def configure(self, input_: ParserSchema) -> None:
        #print("DDDDDDDDDDDDDDDDDDDDDDDDD", input_)
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            named_variables=input_["logFormatVariables"],
        )

    def set_configuration(self) -> None:
        variables = {}
        #print("LLEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEN", self.auto_conf_persistency.get_events_data().items())
        #print("LLEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEN", len(self.auto_conf_persistency.get_events_data().items()))
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_variables_by_classification("STABLE")  # type: ignore
            variables[event_id] = stable_vars
        config_dict = generate_detector_config(
            variable_selection=variables,
            detector_name=self.name,
            method_type=self.config.method_type
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewEventDetectorConfig.from_dict(config_dict, self.name)
