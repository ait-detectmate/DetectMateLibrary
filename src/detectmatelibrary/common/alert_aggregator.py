
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.utils.aux import get_timestamp

from detectmatelibrary.schemas import DetectorSchema, AggregateSchema

from typing_extensions import override
from typing import Any, Optional
from pydantic import Field


def _extract_field(
    input_: list[DetectorSchema] | DetectorSchema, field: str
) -> list[str]:
    if not isinstance(input_, list):
        input_ = [input_]

    return list(set([str(i[field]) for i in input_]))


def _extract_list_fields(
    input_: list[DetectorSchema] | DetectorSchema, field1: str, field2: str
) -> tuple[list[str], list[str]]:

    if not isinstance(input_, list):
        input_ = [input_]

    final1, final2 = [], []
    already_checked = set()
    for in_ in input_:
        for i_1, i_2 in zip(in_[field1], in_[field2]):
            if i_1 not in already_checked:
                final1.append(i_1)
                final2.append(i_2)
                already_checked.add(i_1)

    return final1, final2


class CoreAlertAggregatorConfig(CoreConfig):
    component_type: str = Field(default="alert_aggregators", description="<$IGNORE$>")
    method_type: str = Field(default="core_alert_aggregator", description="<$IGNORE$>")


class CoreAlertAggregator(CoreComponent):
    def __init__(
        self,
        name: str = "CoreAlertAggregator",
        buffer_mode: BufferMode = BufferMode.WINDOW,
        buffer_size: Optional[int] = 1,
        config: CoreAlertAggregatorConfig | dict[str, Any] = CoreAlertAggregatorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = CoreAlertAggregatorConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.method_type,
            config=config,
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
        output_["logIDs"], output_["logTimestamps"] = _extract_list_fields(
            input_, "logIDs", "logTimestamps"
        )

        if (alert := self.aggregate_alerts(input_=input_, output_=output_)):
            output_["aggregatedTimestamp"] = get_timestamp()

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
