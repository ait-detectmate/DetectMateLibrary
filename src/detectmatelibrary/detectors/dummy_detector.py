from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary import schemas

from typing import List, Any


class DummyDetectorConfig(CoreDetectorConfig):
    """Configuration for DummyDetector."""
    method_type: str = "dummy_detector"


class DummyDetector(CoreDetector):
    """A dummy detector for testing purposes."""

    def __init__(
        self,
        name: str = "DummyDetector",
        config: DummyDetectorConfig | dict[str, Any] = DummyDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DummyDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self._call_count = 0

    def detect(
        self,
        input_: List[schemas.ParserSchema_] | schemas.ParserSchema_,
        output_: schemas.DetectorSchema_
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
