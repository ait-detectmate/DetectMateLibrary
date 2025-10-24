from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector
import detectmatelibrary.schemas as schemas

from typing import List, Dict


def replaced_with_sets(d: dict) -> dict:
    new_dict = {}
    for key, value in d.items():
        if isinstance(value, dict):
            # Recursively process nested dicts
            new_dict[key] = replaced_with_sets(value)
        else:
            # Replace innermost (non-dict) values with an empty set
            new_dict[key] = set()
    return new_dict


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

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        """Train the detector by learning values from the input data."""
        if isinstance(self.config.log_variables, AllLogVariables):
            relevant_log_fields = self.config.log_variables[input_.EventID].get_all()
            for var_pos in relevant_log_fields.keys():
                if var_pos not in self.known_values:
                    self.known_values[var_pos] = set()

                if isinstance(var_pos, str):
                    self.known_values[var_pos].add(input_.logFormatVariables[var_pos])
                else:
                    self.known_values[var_pos].add(input_.variables[var_pos])

        elif input_.EventID in self.config.log_variables:
            relevant_log_fields = self.config.log_variables[input_.EventID].get_all()
            if input_.EventID not in self.known_values:
                self.known_values[input_.EventID] = {}
            for var_pos in relevant_log_fields.keys():
                if var_pos not in self.known_values[input_.EventID]:
                    self.known_values[input_.EventID][var_pos] = set()

                if isinstance(var_pos, str):
                    self.known_values[input_.EventID][var_pos].add(input_.logFormatVariables[var_pos])
                else:
                    self.known_values[input_.EventID][var_pos].add(input_.variables[var_pos])

        return None

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data."""
        overall_score = 0.0
        alerts = {}
        if isinstance(self.config.log_variables, AllLogVariables):
            relevant_log_fields = self.config.log_variables[input_.EventID].get_all()

            for var_pos in relevant_log_fields.keys():
                score = 0.0
                if isinstance(var_pos, str):
                    value = input_.logFormatVariables.get(var_pos, None)
                elif len(input_.variables) > var_pos:
                    value = input_.variables[var_pos]
                else:
                    value = None

                if value not in self.known_values[var_pos]:
                    score = 1.0
                    alerts.update({str(var_pos): str(score)})
                overall_score += score

        # TODO: missing single values
        if overall_score > 0:
            output_.score = overall_score
            # Use update() method for protobuf map fields
            output_.alertsObtain.update(alerts)
            return True
        return False
