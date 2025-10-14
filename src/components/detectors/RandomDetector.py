from src.components.common.detector import CoreDetectorConfig, CoreDetector
import src.schemas as schemas

from pydantic import BaseModel
from typing import List
import numpy as np


class RandomDetectorConfig(BaseModel):
    threshold: float = 0.7


class RandomDetector(CoreDetector):
    """Random Detector with hierarchical configuration support."""

    def __init__(
        self, name: str = "RandomDetector", config: CoreDetectorConfig = CoreDetectorConfig()
    ) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        """Train the detector by learning known values from the input data."""
        return

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data.

        Only processes events and variables specified in the
        hierarchical configuration.
        """
        overall_score = 0.0
        alerts = {}
        # get the relevant parts of a log based on config
        relevant_log_fields = self.config.get_relevant_fields(input_)
        for i, (var_name, data) in enumerate(relevant_log_fields.items()):
            # data = {"value": value, "config": config}
            # randomly decide if anomaly or not
            score = np.random.rand()
            if score > data.get("config").threshold:
                # anomaly_detected = True
                score = 1.0
                alerts.update({str(data.get("value")): str(score)})
            overall_score += score
        if overall_score > 0:
            output_.score = overall_score
            # Use update() method for protobuf map fields
            output_.alertsObtain.update(alerts)
            return True
        return False
