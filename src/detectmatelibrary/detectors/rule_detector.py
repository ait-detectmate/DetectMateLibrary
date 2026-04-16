from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary import schemas

from typing import List, Any


class RuleDetectorConfig(CoreDetectorConfig):
    method_type: str = "dummy_detector"


class RuleDetector(CoreDetector):
    def __init__(
        self,
        name: str = "RuleDetector",
        config: RuleDetectorConfig | dict[str, Any] = RuleDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = RuleDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self._call_count = 0

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        return False
