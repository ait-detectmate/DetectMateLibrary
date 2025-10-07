from src.components.common.core import CoreComponent, ConfigCore
from src.components.utils.data_buffer import ArgsBuffer
import src.components.utils.id_generator as op

import src.schemas as schemas

from typing import Literal, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime


class CoreDetectorConfig(ConfigCore):
    detectorID: str = "<PLACEHOLDER>"
    detectorType: str = "<PLACEHOLDER>"

    start_id: int = 0


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


def _generate_default_output(
    input_: List[schemas.ParserSchema] | schemas.ParserSchema,
    config: CoreDetectorConfig
) -> schemas.DetectorSchema:

    return schemas.initialize(
        schema_id=schemas.DETECTOR_SCHEMA,
        **{
            "__version__": "1.0.0",
            "detectorID": config.detectorID,
            "detectorType": config.detectorType,
            "detectionTimestamp": int(datetime.now().timestamp()),
            "logIDs": _extract_logIDs(input_),
            "extractedTimestamps": _extract_timestamp(input_)
        }
    )


class CoreDetector(CoreComponent, ABC):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[CoreDetectorConfig | dict] = CoreDetectorConfig(),
        id_generator: op.SimpleIDGenerator = op.SimpleIDGenerator,
    ):
        if isinstance(config, dict):
            config = CoreDetectorConfig.from_dict(config)

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
        if input_ is None:
            return
        output_ = _generate_default_output(input_=input_, config=self.config)

        self.detect(input_=input_, output_=output_)
        output_.alertID = self.id_generator()
        return output_

    @abstractmethod
    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> None:
        return

    @abstractmethod
    def train(
        self, input_: schemas.ParserSchema | list[schemas.ParserSchema]
    ) -> None: ...

    # def _auto_config(self) -> Any: ...
