
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
from detectmatelibrary.schemas import DetectorSchema, OutputSchema

from typing import Any, Optional


class CoreAlertAggregatorConfig(CoreConfig):
    component_type: str = "alert_aggregators"
    method_type: str = "core_alert_aggregator"


class AlertAggregator(CoreComponent):
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
            type=config.method_type,  # type: ignore
            config=config,  # type: ignore
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=DetectorSchema,
            output_schema=OutputSchema,
        )
