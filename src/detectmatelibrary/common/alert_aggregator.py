
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.schemas import DetectorSchema, AggregateSchema

from typing import Any, Optional
from typing_extensions import override


def _extract_field(
    input_: list[DetectorSchema] | DetectorSchema, field: str
) -> list[str]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [str(i[field]) for i in input_]


def _extract_list_field(input_: list[DetectorSchema] | DetectorSchema, field: str) -> list[str]:
    if not isinstance(input_, list):
        input_ = [input_]

    final = []
    for i in input_:
        final.extend(i[field])

    return final


class CoreAlertAggregatorConfig(CoreConfig):
    component_type: str = "alert_aggregators"
    method_type: str = "core_alert_aggregator"


class CoreAlertAggregator(CoreComponent):
    def __init__(
        self,
        name: str = "CoreAlertAggregator",
        buffer_mode: BufferMode = BufferMode.WINDOW,
        buffer_size: Optional[int] = 1,
        config: Optional[CoreAlertAggregatorConfig | dict[str, Any]] = CoreAlertAggregatorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CoreAlertAggregatorConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.method_type,  # type: ignore
            config=config,  # type: ignore
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=DetectorSchema,
            output_schema=AggregateSchema,
        )

    @override
    def run(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema  # type: ignore
    ) -> bool:

        output_["detectorIDs"] = _extract_field(input_, "detectorID")
        output_["detectorTypes"] = _extract_field(input_, "detectorType")
        output_["alertIDs"] = _extract_field(input_, "alertID")
        output_["logIDs"] = _extract_list_field(input_, "logIDs")
        output_["extractedTimestamps"] = _extract_list_field(input_, "extractedTimestamps")

        if (alert := self.aggregate_alerts(input_=input_, output_=output_)):
            output_["outputTimestamp"] = get_timestamp()

        return alert

    def aggregate_alerts(
        self,
        input_: list[DetectorSchema] | DetectorSchema,
        output_: AggregateSchema,
    ) -> bool:
        return True

    @override
    def train(
        self, input_: DetectorSchema | list[DetectorSchema]  # type: ignore
    ) -> None:
        pass

    @override
    def configure(
        self, input_: DetectorSchema | list[DetectorSchema]  # type: ignore
    ) -> None:
        pass

    @override
    def set_configuration(self) -> None:
        pass

    @override
    def post_train(self) -> None:
        pass
