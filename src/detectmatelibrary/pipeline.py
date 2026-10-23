
from detectmatelibrary.common.core import CoreComponent, CoreConfig

from detectmatelibrary.common.alert_aggregator import CoreAlertAggregator, CoreAlertAggregatorConfig
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode
import detectmatelibrary.helper.select_component as selc

import detectmatelibrary.schemas as sc

from concurrent.futures import ThreadPoolExecutor

from typing import Any, overload, Optional, override
from pydantic import Field


class PipelineConfig(CoreConfig):
    component_type: str = Field(default="main_pipeline", description="<$IGNORE$>")
    method_type: str = Field(default="pipeline", description="<$IGNORE$>")

    do_parsing: bool = Field(default=True, description="Run parser in the pipeline.")
    do_aggregation: bool = Field(default=True, description="Run aggregator in the pipeline.")
    n_workers: int = Field(default=1, description="Workers use to run the detectors in parallel.")

    parser: CoreParserConfig | dict[str, Any] | None = Field(
        default=None, description="Parser configuration use, if do_parsing=False keep empty."
    )
    detectors: list[CoreDetectorConfig | dict[str, Any]] | None = Field(
        default=None, description="Detectors configuration use."
    )
    aggregator: CoreAlertAggregatorConfig | dict[str, Any] | None = Field(
        default=None, description="Aggregator configuration use, if do_aggregation=False keep empty."
    )

# ------------- Auxiliar methods


def _select_input(config: PipelineConfig) -> type[sc.BaseSchema]:
    return sc.LogSchema if config.do_parsing else sc.ParserSchema


def _select_output(config: PipelineConfig) -> type[sc.BaseSchema]:
    return sc.DetectorSchema if config.do_aggregation else sc.AggregateSchema


def _check_output(in_: sc.BaseSchema, method: CoreComponent) -> Optional[bytes | sc.BaseSchema]:
    return method.process(in_)


def _multiprocess(
    methods: list[CoreComponent], in_: sc.BaseSchema, n_workers: int = 4
) -> list[sc.BaseSchema]:

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        outputs = list(executor.map(lambda fn: _check_output(in_, fn), methods))

    return list(filter(lambda x: x is not None, outputs))  # type: ignore


def _run_pipeline(
    config: PipelineConfig,
    input_: sc.ParserSchema | bytes | sc.LogSchema,
    parser: Optional[CoreParser],
    detectors: list[CoreDetector],
    alert_aggreator: Optional[CoreAlertAggregator],
    n_workers: int = 1,
) -> list[sc.DetectorSchema] | list[sc.AggregateSchema]:

    input_ = input_ if isinstance(input_, list) else [input_]  # type: ignore
    if config.do_parsing:
        aux = []
        for in_ in input_:  # type: ignore
            if (out_ := _check_output(in_, parser)) is not None:  # type: ignore
                aux.append(out_)
        input_ = aux   # type: ignore

    output_ = []
    for in_ in input_:  # type: ignore
        if n_workers > 1:
            output_.extend(_multiprocess(detectors, in_=in_, n_workers=n_workers))  # type: ignore
        else:
            for detector in detectors:
                if (out_ := _check_output(in_, detector)) is not None:  # type: ignore
                    output_.append(out_)  # type: ignore

    if not config.do_aggregation:
        return output_   # type: ignore

    last_output_ = []
    for in_ in output_:
        if (out_ := _check_output(in_, alert_aggreator)) is not None:  # type: ignore
            last_output_.append(out_)

    return last_output_  # type: ignore


# ------------- Nain pipeline

class Pipeline(CoreComponent):
    def __init__(
        self,
        name: str = "MainPipeline",
        config: PipelineConfig | dict[str, Any] = PipelineConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = PipelineConfig.from_dict(config, name)

        super().__init__(
            name=name,
            type_=config.method_type,
            config=config,
            args_buffer=ArgsBuffer(mode=BufferMode.NO_BUF, size=None),
            input_schema=_select_input(config),
            output_schema=_select_output(config),
        )
        self.config: PipelineConfig

        self.parser: CoreParser | None = selc.selectComponent(  # type: ignore
            self.config.parser, component_type="parsers"
        ) if self.config.do_parsing else None

        self.detectors: list[CoreDetector] = selc.selectComponents(  # type: ignore
            self.config.detectors, component_type="detectors"
        )

        self.alert_aggregator: CoreAlertAggregator | None = selc.selectComponent(  # type: ignore
            self.config.aggregator, component_type="alert_aggregators"
        ) if self.config.do_aggregation else None

    @overload  # type: ignore
    @override
    def process(self, data: sc.LogSchema | bytes) -> sc.AggregateSchema | bytes | None:  # type: ignore
        pass

    @override
    @overload
    def process(  # type: ignore
        self, data: sc.LogSchema | bytes
    ) -> sc.DetectorSchema | bytes | None | list[sc.DetectorSchema] | list[bytes]:
        pass

    @overload
    @override
    def process(self, data: sc.ParserSchema | bytes) -> sc.AggregateSchema | bytes | None:
        pass

    @overload
    @override
    def process(  # type: ignore
        self, data: sc.ParserSchema | bytes
    ) -> sc.DetectorSchema | bytes | None | list[sc.DetectorSchema] | list[bytes]:
        pass

    @override
    def process(
        self, data: sc.ParserSchema | bytes | sc.LogSchema
    ) -> sc.DetectorSchema | bytes | None | list[sc.DetectorSchema] | list[bytes] | sc.AggregateSchema:

        out_ = _run_pipeline(
            self.config,
            input_=data,
            parser=self.parser,
            detectors=self.detectors,
            alert_aggreator=self.alert_aggregator,
            n_workers=self.config.n_workers,
        )

        if len(out_) == 0:
            return None
        if len(out_) == 1:
            return out_[0]
        return out_  # type: ignore
