from typing import Any, Optional
from components.common.detector import CoreDetector, CoreDetectorConfig
import schemas as schemas


class NVDConfig(CoreDetectorConfig):
    events: list[str] | None = None
    variables: list[str] | None = None
    auto_config_settings: Optional[dict[str, Any]] = None


class NewValueDetector(CoreDetector):
    def __init__(self, name: str = "NewValueDetector", config: NVDConfig = NVDConfig()) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)
        self.value_set = set()

    def train(self, input_: schemas.ParserSchema | list[schemas.ParserSchema]) -> None:
        return

    def detect(
        self, input_: schemas.ParserSchema | list[schemas.ParserSchema], output_: schemas.DetectorSchema
    ) -> bool:
        return False
