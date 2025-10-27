from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector
import detectmatelibrary.schemas as schemas

from typing import Any


# *************** New value methods ****************************************
def _get_element(input_: schemas.ParserSchema, var_pos: str | int) -> Any:
    if isinstance(var_pos, str):
        return input_.logFormatVariables[var_pos]
    elif len(input_.variables) > var_pos:
        return input_.variables[var_pos]


def train_new_values(
    known_values: dict, input_: schemas.ParserSchema, variables: AllLogVariables | LogVariables
) -> None:

    if (relevant_log_fields := variables[input_.EventID]) is None:
        return
    relevant_log_fields = relevant_log_fields.get_all()

    kn_v = known_values
    if isinstance(variables, LogVariables):
        if input_.EventID not in known_values:
            known_values[input_.EventID] = {}
        kn_v = known_values[input_.EventID]

    for var_pos in relevant_log_fields.keys():
        if var_pos not in kn_v:
            kn_v[var_pos] = set()

        kn_v[var_pos].add(_get_element(input_, var_pos=var_pos))


def detect_new_values(
    known_values: dict,
    input_: schemas.ParserSchema,
    variables: AllLogVariables | LogVariables,
    alerts: dict,
) -> int:

    overall_score, alerts = 0.0, {}
    if (relevant_log_fields := variables[input_.EventID]) is None:
        return 0.
    relevant_log_fields = relevant_log_fields.get_all()

    kn_v = known_values
    if isinstance(variables, LogVariables):
        if input_.EventID not in known_values:
            return overall_score
        kn_v = known_values[input_.EventID]

    for var_pos in relevant_log_fields.keys():
        score = 0.0
        value = _get_element(input_, var_pos=var_pos)

        if value not in kn_v[var_pos]:
            score = 1.0
            alerts.update({"New variable": str(var_pos)})
        overall_score += score

    return overall_score

# ************************************************************************

class NewValueDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_detector"

    log_variables: LogVariables | AllLogVariables = {}


class NewValueDetector(CoreDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self, name: str = "NewValueDetector", config: CoreDetectorConfig = CoreDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewValueDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode="no_buf", config=config)
        self.known_values = {}

    def train(self, input_: schemas.ParserSchema) -> None:
        """Train the detector by learning values from the input data."""
        train_new_values(
            known_values=self.known_values, input_=input_, variables=self.config.log_variables
        )

    def detect(
        self, input_:  schemas.ParserSchema, output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data."""
        alerts = {}

        overall_score = detect_new_values(
            known_values=self.known_values,
            input_=input_,
            variables=self.config.log_variables,
            alerts={}
        )

        if overall_score > 0:
            output_.score = overall_score
            output_.alertsObtain.update(alerts)
            return True

        return False
