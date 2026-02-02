from detectmatelibrary.common._config import generate_detector_config
from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.common.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker
)
from detectmatelibrary.common.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing import Any


# *************** New value methods ****************************************
def _get_element(input_: ParserSchema, var_pos: str | int) -> Any:
    if isinstance(var_pos, str):
        return input_["logFormatVariables"][var_pos]
    elif len(input_["variables"]) > var_pos:
        return input_["variables"][var_pos]


def train_new_values(
    known_values: dict[str, set[Any] | dict[str, Any]],
    input_: ParserSchema,
    variables: AllLogVariables | LogVariables
) -> None:

    if (relevant_log_fields := variables[input_["EventID"]]) is None:
        return
    relevant_log_fields = relevant_log_fields.get_all()  # type: ignore

    kn_v = known_values
    if isinstance(variables, LogVariables):
        if input_["EventID"] not in known_values:
            known_values[input_["EventID"]] = {}
        kn_v = known_values[input_["EventID"]]  # type: ignore

    for var_pos in relevant_log_fields.keys():  # type: ignore
        if var_pos not in kn_v:
            kn_v[var_pos] = set()

        kn_v[var_pos].add(_get_element(input_, var_pos=var_pos))  # type: ignore


def detect_new_values(
    known_values: dict[str, Any],
    input_: ParserSchema,
    variables: AllLogVariables | LogVariables,
    alerts: dict[str, str],
) -> float:

    overall_score = 0.0
    if (relevant_log_fields := variables[input_["EventID"]]) is None:
        return 0.
    relevant_log_fields = relevant_log_fields.get_all()  # type: ignore

    kn_v = known_values
    if isinstance(variables, LogVariables):
        if input_["EventID"] not in known_values:
            return overall_score
        kn_v = known_values[input_["EventID"]]

    for var_pos in relevant_log_fields.keys():  # type: ignore
        score = 0.0
        value = _get_element(input_, var_pos=var_pos)

        if value not in kn_v[var_pos]:
            score = 1.0
            alerts.update({f"New variable in {var_pos}": str(value)})
        overall_score += score

    return overall_score


#  ************************************************************************
class NewValueDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_detector"

    log_variables: LogVariables | AllLogVariables | dict[str, Any] = {}


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
        configured_variables = self.get_configured_variables(input_, self.config.log_variables)
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

        configured_variables = self.get_configured_variables(input_, self.config.log_variables)

        overall_score = 0.0

        for event_id, event_tracker in self.persistency.get_events_data().items():
            for event_id, multi_tracker in event_tracker.get_data().items():
                value = configured_variables.get(event_id)
                if value is None:
                    continue
                if value not in multi_tracker.unique_set:
                    alerts[f"EventID {event_id}"] = (
                        f"Unknown value: {value} detected."
                    )
                    overall_score += 1.0

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = "Method that detect new values in the logs"
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
        templates = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_variables_by_classification("STABLE")  # type: ignore
            variables[event_id] = stable_vars
            templates[event_id] = self.auto_conf_persistency.get_event_template(event_id)
        config_dict = generate_detector_config(
            variable_selection=variables,
            templates=templates,
            detector_name=self.name,
            method_type=self.config.method_type,
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewValueDetectorConfig.from_dict(config_dict, self.name)
