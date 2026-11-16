from typing import Any, List

from detectmatelibrary.base_detectors import CountVectorDetector, CountVectorDetectorConfig
from detectmatelibrary.utils.sequence_encoding import count_events, encode_count_vec
from detectmatelibrary import schemas

from pydantic import Field


class SCVSDetectorConfig(CountVectorDetectorConfig):
    method_type: str = Field(
        default="scvs_detector", description="Indicates what type of method it is."
    )


class SCVSDetector(CountVectorDetector):
    def __init__(
        self,
        name: str = "SCVSDetector",
        config: SCVSDetectorConfig | dict[str, Any] = SCVSDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = SCVSDetectorConfig.from_dict(config, name)
        super().__init__(name=name, config=config)
        self.config: SCVSDetectorConfig

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema,
    ) -> bool:

        events = self.window_events(input_)
        key = encode_count_vec(self.config.window_size, count_events(events))
        if key not in self.persistency.get_events_seen():
            output_["score"] = 1.
            output_["description"] = "Count vector not found"
            return True

        return False
