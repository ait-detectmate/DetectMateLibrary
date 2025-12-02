from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing import Any, cast


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
        self, name: str = "NewValueDetector", config: CoreDetectorConfig = CoreDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewValueDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

        self.config = cast(NewValueDetectorConfig, self.config)
        self.known_values: dict[str, Any] = {}

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        train_new_values(
            known_values=self.known_values, input_=input_, variables=self.config.log_variables  # type: ignore
        )

    def detect(
        self, input_:  ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        """Detect new values in the input data."""
        alerts: dict[str, str] = {}

        overall_score = detect_new_values(
            known_values=self.known_values,
            input_=input_,
            variables=self.config.log_variables,  # type: ignore
            alerts=alerts
        )

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = "Method that detect new value in the logs"
            output_["alertsObtain"].update(alerts)
            return True

        return False
