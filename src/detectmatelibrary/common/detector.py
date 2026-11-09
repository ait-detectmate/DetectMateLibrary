from detectmatelibrary.common._config._formats import EventsConfig, _EventInstance
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing import Dict, List, Optional, Any
from typing_extensions import override
from pydantic import Field

from detectmatelibrary.utils.time_format_handler import TimeFormatHandler


_time_handler = TimeFormatHandler()


def _extract_timestamp(input_: List[ParserSchema] | ParserSchema) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]
    return [
        int(_time_handler.parse_timestamp(i["headerVariables"]["Time"]))
        for i in input_
    ]


def _extract_logIDs(input_: List[ParserSchema] | ParserSchema) -> List[str]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [str(i["logID"]) for i in input_]


def define_name(name: str, parser: Optional[str]) -> str:
    return name if parser is None else f"{name}_from_{parser}"


class CoreDetectorConfig(CoreConfig):
    component_type: str = Field(default="detectors", description="<$IGNORE$>")
    method_type: str = Field(default="core_detector", description="<$IGNORE$>")
    parser: Optional[str] = Field(default=None, description="Name of the parser used.")

    auto_config: bool = Field(
        default=True,
        description=(
            "Runs the configuration step before the training process. "
            "Has no effect unless data_use_configure is set."
        ),
    )
    events: EventsConfig | dict[str, Any] = Field(
        default={},
        description=EventsConfig.__doc__,
    )
    global_instances: Dict[str, _EventInstance] = Field(
        default={},
        description=(
            "Instances monitoring event-independent header variables (e.g. hostname, level), "
            "keyed by instance name. Written as `global` in YAML."
        ),
    )


class CoreDetector(CoreComponent[ParserSchema, DetectorSchema]):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: BufferMode = BufferMode.NO_BUF,
        buffer_size: Optional[int] = None,
        config: CoreDetectorConfig | dict[str, Any] = CoreDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CoreDetectorConfig.from_dict(config, name)

        super().__init__(
            name=define_name(name, config.parser),
            type_=config.component_type,
            config=config,
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=ParserSchema,
            output_schema=DetectorSchema,
        )
        self.config: CoreDetectorConfig

    @override
    def run(
        self,
        input_: List[ParserSchema] | ParserSchema,
        output_: DetectorSchema,
    ) -> bool:

        output_["detectorID"] = self.name
        output_["detectorType"] = self.config.method_type
        output_["logIDs"] = _extract_logIDs(input_)
        output_["logTimestamps"] = _extract_timestamp(input_)
        output_["receivedTimestamp"] = get_timestamp()

        if anomaly_detected := self.detect(input_=input_, output_=output_):
            output_["alertID"] = str(self.id_generator())
            output_["detectedTimestamp"] = get_timestamp()

        return anomaly_detected

    @override
    def _is_input_eligible(self, data: ParserSchema) -> bool:  # type: ignore
        return self.config.parser is None or self.config.parser == data["parserID"]

    def detect(
        self,
        input_: List[ParserSchema] | ParserSchema,
        output_: DetectorSchema,
    ) -> bool:
        return True

    @override
    def train(
        self,
        input_: ParserSchema | list[ParserSchema],
    ) -> None:
        pass

    @override
    def configure(
        self,
        input_: ParserSchema | list[ParserSchema],
    ) -> None:
        pass
