from ..common.detector import CoreDetector, CoreDetectorConfig
from .. import schemas

from typing import List
import numpy as np


class DummyDetectorConfig(CoreDetectorConfig):
    """Configuration for DummyDetector."""
    pass


class DummyDetector(CoreDetector):
    """A dummy detector for testing purposes."""

    def __init__(
        self,
        name: str = "DummyDetector",
        config: DummyDetectorConfig | dict = DummyDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DummyDetectorConfig.from_dict(config)
        super().__init__(name=name, buffer_mode="no_buf", config=config)

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool | None:
        output_.description = "Dummy detection process"
        if np.random.rand() > 0.5:
            output_.score = 1.0
            output_.alertsObtain["type"] = "Anomaly detected by DummyDetector"
            return True
