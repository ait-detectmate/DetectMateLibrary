from detectmatelibrary.common.core import CoreComponent, CoreConfig, CoreComponent

from typing import List, Optional, Any

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.schemas import ParserSchema_, DetectorSchema_  # type: ignore


def _extract_timestamp(
    input_: List[ParserSchema_] | ParserSchema_
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [int(float(i.logFormatVariables["Time"])) for i in input_]  # type: ignore


def _extract_logIDs(
    input_: List[ParserSchema_] | ParserSchema_
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [i.logID for i in input_]  # type: ignore


class CoreDetectorConfig(CoreConfig):
    comp_type: str = "detectors"
    method_type: str = "core_detector"
    parser: str = "<PLACEHOLDER>"

    auto_config: bool = False


class CoreDetector(CoreComponent):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: BufferMode = BufferMode.NO_BUF,
        buffer_size: Optional[int] = None,
        config: Optional[CoreDetectorConfig | dict[str, Any]] = CoreDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CoreDetectorConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.comp_type,  # type: ignore
            config=config,  # type: ignore
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=ParserSchema_,  # type: ignore
            output_schema=DetectorSchema_,  # type: ignore
        )

    def run(
        self,
        input_: List[ParserSchema_] | ParserSchema_, # type: ignore
        output_: DetectorSchema_ # type: ignore
    ) -> bool:

        output_.detectorID = self.name  # type: ignore
        output_.detectorType = self.config.method_type  # type: ignore
        output_.logIDs.extend(_extract_logIDs(input_))  # type: ignore
        output_.extractedTimestamps.extend(_extract_timestamp(input_))  # type: ignore
        output_.alertID = self.id_generator()  # type: ignore
        output_.receivedTimestamp = get_timestamp()  # type: ignore

        anomaly_detected = self.detect(input_=input_, output_=output_)
        output_.detectionTimestamp = get_timestamp()  # type: ignore

        return True if anomaly_detected is None else anomaly_detected

    def detect(
        self,
        input_: List[ParserSchema_] | ParserSchema_,
        output_: DetectorSchema_ ,
    ) -> bool | None:
        return True

    def train(
        self, input_: ParserSchema_ | list[ParserSchema_]  # type: ignore
    ) -> None: ...
