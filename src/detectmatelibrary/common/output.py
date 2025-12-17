from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.schemas import DetectorSchema, OutputSchema, FieldNotFound

from typing_extensions import override
from typing import List, Optional, Any


class CoreOutputConfig(CoreConfig):
    comp_type: str = "outputs"
    method_type: str = "core_output"

    auto_config: bool = False


class DetectorFieldNotFound(Exception):
    pass


def get_field(input_: List[DetectorSchema] | DetectorSchema, field: str) -> List[Any]:
    try:
        if isinstance(input_, list):
            if input_[0].is_field_list(field):
                return [item for detector in input_ for item in detector[field]]
            return [detector[field] for detector in input_]
        else:
            return [input_[field]]
    except FieldNotFound:
        raise DetectorFieldNotFound()


class CoreOutput(CoreComponent):
    def __init__(
        self,
        name: str = "CoreOutput",
        buffer_mode: BufferMode = BufferMode.NO_BUF,
        buffer_size: Optional[int] = None,
        config: Optional[CoreOutputConfig | dict[str, Any]] = CoreOutputConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CoreOutputConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.comp_type,  # type: ignore
            config=config,  # type: ignore
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=DetectorSchema,
            output_schema=OutputSchema,
        )

    @override
    def run(
        self, input_: List[DetectorSchema] | DetectorSchema, output_: OutputSchema  # type: ignore
    ) -> bool:
        output_["detectorIDs"] = get_field(input_, "detectorID")
        output_["detectorTypes"] = get_field(input_, "detectorType")
        output_["alertIDs"] = get_field(input_, "alertID")
        output_["logIDs"] = get_field(input_, "logIDs")
        output_["extractedTimestamps"] = get_field(input_, "extractedTimestamps")

        do_output = self.do_output(input_, output_)
        output_["outputTimestamp"] = get_timestamp()

        return do_output if do_output is not None else True

    def do_output(
        self,
        input_: List[DetectorSchema] | DetectorSchema,
        output_: OutputSchema,
    ) -> bool | None:
        return True

    @override
    def train(
        self, input_: DetectorSchema | list[DetectorSchema]  # type: ignore
    ) -> None:
        pass
