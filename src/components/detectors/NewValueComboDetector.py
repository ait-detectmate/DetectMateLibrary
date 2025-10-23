from src.components.common.config.detector import CoreDetectorConfig
from src.components.common.detector import CoreDetector
from src.utils.functions import sorted_int_str
import src.schemas as schemas

from pydantic import BaseModel
from typing import List


class NewValueComboDetectorConfig(BaseModel):
    pass


class NewValueComboDetector(CoreDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self, name: str = "NewValueComboDetector", config: CoreDetectorConfig = CoreDetectorConfig()
    ) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)
        self.known_combos = self._prepare_known_combos()

    def _prepare_known_combos(self) -> dict:
        """Prepare the known combinations dictionary based on the
        configuration."""
        known_combos = {}
        for event_id in self.config._all_instances_dict.keys():
            var_combo = tuple(sorted_int_str(
                self.config._all_instances_dict[event_id].keys())
            )
            known_combos[event_id] = {var_combo: set()}
        return known_combos

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        """Train the detector by learning values from the input data."""
        relevant_log_fields = self.config.get_relevant_fields(input_)
        var_combo = tuple(sorted_int_str(relevant_log_fields.keys()))
        if var_combo in self.known_combos.get(input_.EventID, []):
            val_combo = tuple(field["value"] for field in relevant_log_fields.values())
            self.known_combos[input_.EventID][var_combo].add(val_combo)

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

        var_combo = tuple(sorted_int_str(relevant_log_fields.keys()))
        if var_combo in self.known_combos.get(input_.EventID, []):
            val_combo = tuple(field["value"] for field in relevant_log_fields.values())
            is_combo_known = val_combo in self.known_combos[input_.EventID][var_combo]
            if not is_combo_known:
                score = 1.0
                alerts.update({str(val_combo): str(score)})
            overall_score += score
        if overall_score > 0:
            output_.score = overall_score
            # Use update() method for protobuf map fields
            output_.alertsObtain.update(alerts)
            return True
        return False
