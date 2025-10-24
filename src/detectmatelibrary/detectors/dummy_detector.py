from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary import schemas

from typing import List


class DummyDetectorConfig(CoreDetectorConfig):
    """Configuration for DummyDetector."""
    method_type: str = "dummy_detector"


class DummyDetector(CoreDetector):
    """A dummy detector for testing purposes."""

    def __init__(
        self,
        name: str = "DummyDetector",
        config: DummyDetectorConfig | dict = DummyDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DummyDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode="no_buf", config=config)
        self._call_count = 0

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool | None:
        output_.description = "Dummy detection process"

        # Alternating pattern: True, False, True, False, etc
        self._call_count += 1
        pattern = [True, False]
        result = pattern[self._call_count % len(pattern)]
        if result:
            output_.score = 1.0
            output_.alertsObtain["type"] = "Anomaly detected by DummyDetector"
        return result
