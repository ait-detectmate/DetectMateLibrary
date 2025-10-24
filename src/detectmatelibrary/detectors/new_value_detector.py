from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector
import detectmatelibrary.schemas as schemas

from typing import List, Dict


# *************** Train methods ****************************************
def train_all(known_values: dict, input_: schemas.ParserSchema, variables: AllLogVariables) -> None:
    relevant_log_fields = variables[input_.EventID].get_all()
    for var_pos in relevant_log_fields.keys():
        if var_pos not in known_values:
            known_values[var_pos] = set()

        if isinstance(var_pos, str):
            known_values[var_pos].add(input_.logFormatVariables[var_pos])
        else:
            known_values[var_pos].add(input_.variables[var_pos])


def train_multiple(
    known_values: dict, input_: schemas.ParserSchema, variables: Dict[int, LogVariables]
) -> None:
    relevant_log_fields = variables[input_.EventID].get_all()
    if input_.EventID not in known_values:
        known_values[input_.EventID] = {}
    for var_pos in relevant_log_fields.keys():
        if var_pos not in known_values[input_.EventID]:
            known_values[input_.EventID][var_pos] = set()

        if isinstance(var_pos, str):
            known_values[input_.EventID][var_pos].add(input_.logFormatVariables[var_pos])
        else:
            known_values[input_.EventID][var_pos].add(input_.variables[var_pos])

# *************** Detect methods ****************************************
def detect_all(
    known_values: dict,
    input_: schemas.ParserSchema,
    variables: AllLogVariables,
    alerts: dict,
    overall_score: int,
) -> int:
    relevant_log_fields = variables[input_.EventID].get_all()

    for var_pos in relevant_log_fields.keys():
        score = 0.0
        if isinstance(var_pos, str):
            value = input_.logFormatVariables.get(var_pos, None)
        elif len(input_.variables) > var_pos:
            value = input_.variables[var_pos]
        else:
            value = None

        if value not in known_values[var_pos]:
            score = 1.0
            alerts.update({str(var_pos): str(score)})
        overall_score += score

    return overall_score


def detect_multiple(
    known_values: dict,
    input_: schemas.ParserSchema,
    variables: AllLogVariables,
    alerts: dict,
    overall_score: int,
) -> int:
    relevant_log_fields = variables[input_.EventID].get_all()

    for var_pos in relevant_log_fields.keys():
        score = 0.0
        if isinstance(var_pos, str):
            value = input_.logFormatVariables[var_pos]
        else:
            value = input_.variables[var_pos]

        if value not in known_values[input_.EventID][var_pos]:
            score = 1.0
            alerts.update({str(var_pos): str(score)})
        overall_score += score

    return overall_score

# ************************************************************************
class NewValueDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_detector"

    log_variables: Dict[int, LogVariables] | AllLogVariables = {}


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
        train_method = train_multiple
        if isinstance(self.config.log_variables, AllLogVariables):
            train_method = train_all
        elif input_.EventID not in self.config.log_variables:
            return

        train_method(
            known_values=self.known_values, input_=input_, variables=self.config.log_variables
        )

    def detect(
        self, input_:  schemas.ParserSchema, output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data."""
        overall_score, alerts = 0.0, {}

        if isinstance(self.config.log_variables, AllLogVariables):
            overall_score = detect_all(
                known_values=self.known_values,
                input_=input_,
                variables=self.config.log_variables,
                alerts=alerts,
                overall_score=overall_score
            )
        elif input_.EventID in self.config.log_variables:
            overall_score = detect_multiple(
                known_values=self.known_values,
                input_=input_,
                variables=self.config.log_variables,
                alerts=alerts,
                overall_score=overall_score
            )

        if overall_score > 0:
            output_.score = overall_score
            output_.alertsObtain.update(alerts)
            return True

        return False
