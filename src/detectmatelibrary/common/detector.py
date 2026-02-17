from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from typing_extensions import override
from typing import Dict, List, Optional, Any


def _extract_timestamp(
    input_: List[ParserSchema] | ParserSchema
) -> List[int]:
    def format_time(time: str) -> int:
        time_ = time.split(":")[0]
        return int(float(time_))

    if not isinstance(input_, list):
        input_ = [input_]

    return [format_time(i["logFormatVariables"]["Time"]) for i in input_]


def _extract_logIDs(
    input_: List[ParserSchema] | ParserSchema
) -> List[str]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [str(i["logID"]) for i in input_]


def get_configured_variables(
        input_: ParserSchema,
        log_variables: EventsConfig | dict[str, Any],
) -> Dict[str, Any]:
    """Extract variables from input based on what's defined in the config.

    Args:
        input_: Parser schema containing variables and logFormatVariables
        log_variables: Config specifying which variables to extract per EventID

    Returns:
        Dict mapping variable names to their values from the input
    """
    event_id = input_["EventID"]
    result: Dict[str, Any] = {}

    # Get the config for this event
    event_config = log_variables[event_id] if event_id in log_variables else None
    if event_config is None:
        return result

    # Extract template variables by position
    if hasattr(event_config, "variables"):
        for pos, var in event_config.variables.items():
            if pos < len(input_["variables"]):
                result[var.name] = input_["variables"][pos]

    # Extract header/log format variables by name
    if hasattr(event_config, "header_variables"):
        for name in event_config.header_variables:
            if name in input_["logFormatVariables"]:
                result[name] = input_["logFormatVariables"][name]

    return result


class CoreDetectorConfig(CoreConfig):
    comp_type: str = "detectors"
    method_type: str = "core_detector"
    parser: str = "<PLACEHOLDER>"

    auto_config: bool = True


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
            input_schema=ParserSchema,
            output_schema=DetectorSchema,
        )

    @override
    def run(
        self, input_: List[ParserSchema] | ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:

        output_["detectorID"] = self.name
        output_["detectorType"] = self.config.method_type
        output_["logIDs"] = _extract_logIDs(input_)
        output_["extractedTimestamps"] = _extract_timestamp(input_)
        output_["receivedTimestamp"] = get_timestamp()

        if (anomaly_detected := self.detect(input_=input_, output_=output_)):
            output_["alertID"] = str(self.id_generator())
            output_["detectionTimestamp"] = get_timestamp()

        return anomaly_detected

    def detect(
        self,
        input_: List[ParserSchema] | ParserSchema,
        output_: DetectorSchema,
    ) -> bool:
        return True

    @override
    def train(
        self, input_: ParserSchema | list[ParserSchema]  # type: ignore
    ) -> None:
        pass
