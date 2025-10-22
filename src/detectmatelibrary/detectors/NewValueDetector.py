from detectmatelibrary.common.config.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector
import detectmatelibrary.schemas as schemas

from pydantic import BaseModel
from typing import List


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


class NewValueDetectorConfig(BaseModel):
    pass


class NewValueDetector(CoreDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self, name: str = "NewValueDetector", config: CoreDetectorConfig = CoreDetectorConfig()
    ) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)
        self.known_values = replaced_with_sets(config._all_instances_dict)

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        """Train the detector by learning values from the input data."""
        relevant_log_fields = self.config.get_relevant_fields(input_)
        if "all" in self.known_values:
            for var_pos, data in relevant_log_fields.items():
                if var_pos in self.known_values["all"]:
                    self.known_values["all"][var_pos].add(data.get("value"))
        if input_.EventID in self.known_values:
            for i, (var_pos, data) in enumerate(relevant_log_fields.items()):
                if var_pos in self.known_values[input_.EventID]:
                    self.known_values[input_.EventID][var_pos].add(data.get("value"))
        return None

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data."""
        overall_score = 0.0
        alerts = {}
        # get the relevant parts of a log based on config
        relevant_log_fields = self.config.get_relevant_fields(input_)
        for i, (var_pos, data) in enumerate(relevant_log_fields.items()):
            val = data.get("value")
            score = 0.0
            is_val_known = val in self.known_values["all"][var_pos] or \
                val in self.known_values.get(input_.EventID, {}).get(var_pos, set())
            if not is_val_known:
                score = 1.0
                alerts.update({str(val): str(score)})
            overall_score += score
        if overall_score > 0:
            output_.score = overall_score
            # Use update() method for protobuf map fields
            output_.alertsObtain.update(alerts)
            return True
        return False
