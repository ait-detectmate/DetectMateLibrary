from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.data_buffer import BufferMode

import detectmatelibrary.schemas as schemas

from typing import List, Any
import numpy as np


class RandomDetectorConfig(CoreDetectorConfig):
    method_type: str = "random_detector"

    log_variables: LogVariables | AllLogVariables | dict[str, Any] = {}


class RandomDetector(CoreDetector):
    """Detects anomalies randomly in logs, completely independent of the input
    data."""

    def __init__(
        self, name: str = "RandomDetector", config: RandomDetectorConfig = RandomDetectorConfig()
    ) -> None:
        if isinstance(config, dict):
            config = RandomDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUFF, config=config)

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        """Training is not applicable for RandomDetector."""
        return

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        """Detect anomalies randomly in the input data."""
        overall_score = 0.0
        alerts = {}

        relevant_log_fields = self.config.log_variables[input_.EventID].get_all()   # type: ignore
        for log_variable in relevant_log_fields.values():
            score = 0.0
            random = np.random.rand()
            if random > log_variable.params["threshold"]:
                score = 1.0
                alerts.update({log_variable.name: str(score)})
            overall_score += score

        if overall_score > 0:
            output_.score = overall_score
            output_.alertsObtain.update(alerts)
            return True

        return False
