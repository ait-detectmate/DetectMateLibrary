from src.components.common.core import CoreComponent, ConfigCore
from src.components.utils.data_buffer import ArgsBuffer
import src.components.common._op as op

import src.schemas as schemas

from typing import Any, Literal, Optional, List, Callable
from abc import ABC, abstractmethod


def _extract_timestamp(
    input_: List[schemas.ParserSchema] | schemas.ParserSchema
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [int(i.logFormatVariables["timestamp"]) for i in input_]


class DetectorConfig(ConfigCore):
    detectorID: str = "<PLACEHOLDER>"
    detectorType: str = "<PLACEHOLDER>"

    get_timestamp: Callable[[], int] = op.current_timestamp
    start_id: int = 0


class CoreDetector(CoreComponent, ABC):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[DetectorConfig | dict] = DetectorConfig(),
        id_generator: op.LogIDGenerator = op.LogIDGenerator,
    ):
        if isinstance(config, dict):
            config = DetectorConfig.from_dict(config)

        super().__init__(
            name=name,
            type_="Detector",
            config=config,
            train_function=self.train,
            process_function=self.run,
            args_buffer=ArgsBuffer(
                mode=buffer_mode, size=buffer_size
            ),
            input_schema=schemas.PARSER_SCHEMA,
            output_schema=schemas.DETECTOR_SCHEMA,
        )
        self.id_generator = id_generator(self.config.start_id)

    def run(
        self, input_: List[schemas.ParserSchema] | schemas.ParserSchema
    ) -> schemas.DetectorSchema | None:
        output_ = schemas.initialize(
            schema_id=self.output_schema,
            **{
                "__version__": "1.0.0",
                "detectorID": self.config.detectorID,
                "detectorType": self.config.detectorType,
                "alertID": self.id_generator(),
                "detectionTimestamp": self.config.get_timestamp(),
                "predictionLabel": False,
                "score": 0.0,
                "extractedTimestamps": _extract_timestamp(input_)
            }
        )
        if self.detect(input_=input_, output_=output_):
            return output_
        else:
            None

    @abstractmethod
    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        return False

    @abstractmethod
    def train(self, data: Any) -> None: ...
