from detectmatelibrary.common._config._formats import EventsConfig, Variable

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.data_buffer import BufferMode

import detectmatelibrary.schemas as schemas

from typing_extensions import override
from typing import List, Any
import numpy as np


class RandomDetectorConfig(CoreDetectorConfig):
    method_type: str = "random_detector"

    events: EventsConfig | dict[str, Any] = {}


class RandomDetector(CoreDetector):
    """Detects anomalies randomly in logs, completely independent of the input
    data."""

    def __init__(
        self, name: str = "RandomDetector", config: RandomDetectorConfig = RandomDetectorConfig()
    ) -> None:
        if isinstance(config, dict):
            config = RandomDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: RandomDetectorConfig

    @override
    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:  # type: ignore
        """Training is not applicable for RandomDetector."""
        return

    @override
    def detect(
        self, input_: schemas.ParserSchema, output_: schemas.DetectorSchema  # type: ignore
    ) -> bool:
        """Detect anomalies randomly in the input data."""
        overall_score = 0.0
        alerts = {}

        event_config = self.config.events[input_["EventID"]]
        if event_config is None:
            return False

        relevant_log_fields = event_config.get_all()
        for log_variable in relevant_log_fields.values():
            score = 0.0
            random = np.random.rand()
            if random > log_variable.params["threshold"]:
                score = 1.0
                # Variable has .name, Header has .pos (str)
                var_name = log_variable.name if isinstance(log_variable, Variable) else log_variable.pos
                alerts.update({var_name: str(score)})
            overall_score += score

        if overall_score > 0:
            output_["score"] = overall_score
            output_["alertsObtain"].update(alerts)
            return True

        return False
