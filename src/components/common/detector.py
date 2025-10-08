from src.components.common.core import CoreComponent, CoreConfig

from src.utils.data_buffer import ArgsBuffer

import src.schemas as schemas

from typing import Literal, Optional, List
from datetime import datetime


class CoreDetectorConfig(CoreConfig):
    detectorID: str = "<PLACEHOLDER>"
    detectorType: str = "<PLACEHOLDER>"


def _extract_timestamp(
    input_: List[schemas.ParserSchema] | schemas.ParserSchema
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [int(i.logFormatVariables["timestamp"]) for i in input_]


def _extract_logIDs(
    input_: List[schemas.ParserSchema] | schemas.ParserSchema
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [i.logID for i in input_]


class CoreDetector(CoreComponent):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[CoreDetectorConfig | dict] = CoreDetectorConfig(),
    ):
        if isinstance(config, dict):
            config = CoreDetectorConfig.from_dict(config)

        super().__init__(
            name=name,
            type_="Detector",
            config=config,
            args_buffer=ArgsBuffer(
                mode=buffer_mode, size=buffer_size
            ),
            input_schema=schemas.PARSER_SCHEMA,
            output_schema=schemas.DETECTOR_SCHEMA,
        )

    def run(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> None:

        output_.logIDs.extend(_extract_logIDs(input_))
        output_.extractedTimestamps.extend(_extract_timestamp(input_))
        output_.alertID = self.id_generator()
        output_.receivedTimestamp = int(datetime.now().timestamp())

        self.detect(input_=input_, output_=output_)
        output_.detectionTimestamp = int(datetime.now().timestamp())

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> None:
        return

    def train(
        self, input_: schemas.ParserSchema | list[schemas.ParserSchema]
    ) -> None: ...
