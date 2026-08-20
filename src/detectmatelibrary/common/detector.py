from detectmatelibrary.common._config._formats import EventsConfig, _EventInstance
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp
from detectmatelibrary.utils import persistency
from detectmatelibrary.common.persist import init_persistency

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from pydantic import BaseModel, ConfigDict
from typing_extensions import override
from typing import Dict, List, Optional, Any, cast

from detectmatelibrary.utils.persistency.component_interfaces import PersistConfig
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler


_time_handler = TimeFormatHandler()


def _extract_timestamp(
    input_: List[ParserSchema] | ParserSchema
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]
    return [int(_time_handler.parse_timestamp(i["logFormatVariables"]["Time"])) for i in input_]


def _extract_logIDs(
    input_: List[ParserSchema] | ParserSchema
) -> List[str]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [str(i["logID"]) for i in input_]


class AutoConfigParams(BaseModel):
    """Inputs to the auto-configuration (configure) phase.

    Empty here: the core detector has no configure-phase inputs. Subclasses
    add the fields their detector's configure phase reads. Kept apart from the
    operational `params` block so the phase a setting belongs to is visible in
    the YAML, not just in the code that reads it.
    """

    model_config = ConfigDict(extra="forbid")


class CoreDetectorConfig(CoreConfig):
    component_type: str = "detectors"
    method_type: str = "core_detector"
    parser: str = "<PLACEHOLDER>"

    auto_config: bool = True
    auto_config_params: AutoConfigParams = AutoConfigParams()
    events: EventsConfig | dict[str, Any] = {}
    global_instances: Dict[str, _EventInstance] = {}
    persist: PersistConfig | None = None


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
            type_=config.component_type,  # type: ignore
            config=config,  # type: ignore
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=ParserSchema,
            output_schema=DetectorSchema,
        )

    def _register_persistency(self, event_persistency: persistency.EventPersistency) -> None:
        self.saver = init_persistency(
            self.name, cast(CoreDetectorConfig, self.config), event_persistency
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

    @override
    def configure(
        self, input_: ParserSchema | list[ParserSchema]  # type: ignore
    ) -> None:
        pass

    @override
    def set_configuration(self) -> None:
        pass

    @override
    def post_train(self) -> None:
        pass
