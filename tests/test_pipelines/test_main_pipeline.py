from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

from detectmatelibrary.pipeline import PipelineConfig, _run_pipeline, Pipeline

from detectmatelibrary._testutils.dummy_parser import DummyParser
from detectmatelibrary._testutils.dummy_detector import DummyDetectorConfig
from detectmatelibrary._testutils.dummy_alert_aggregator import (
    DummyAlertAggregator, DummyAlertAggregatorConfig
)

from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc

from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig

from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig

from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig

import pytest


class AlwayAlert(CoreDetector):
    """A dummy detector for testing purposes."""

    def __init__(
        self,
        name: str = "DummyDetector",
        config: DummyDetectorConfig = DummyDetectorConfig()
    ) -> None:

        super().__init__(name=name, config=config)

    def detect(
        self,
        input_: list[sc.ParserSchema] | sc.ParserSchema,
        output_: sc.DetectorSchema
    ) -> bool:
        output_["description"] = "Dummy detection process"

        output_["score"] = 1.0
        output_["alertDetails"]["type"] = "Anomaly detected by DummyDetector"
        return True


log_schema = sc.LogSchema({"logID": "1", "log": "hello"})

parser_schema = sc.ParserSchema({
    "parserType": "a",
    "parserID": "ciao",
    "logID": "1",
    "eventID": 1,
    "template": "a",
    "parsedLogID": "as2",
    "log": "hello",
    "receivedTimestamp": 1,
    "parsedTimestamp": 2,
    "headerVariables": {"Time": "-1"}
})


class TestRunPipeline:
    def test_run_parser2detectors(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=False),
            input_=log_schema,
            parser=DummyParser(),
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=None
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.DetectorSchema)
        assert len(out_) == 2

    def test_run_parser2aggregator(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=True),
            input_=log_schema,
            parser=DummyParser(),
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=DummyAlertAggregator(
                config=DummyAlertAggregatorConfig(buffer_size=2)
            )
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.AggregateSchema)
        assert len(out_) == 1

    def test_run_detectors_only(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=False, do_aggregation=False),
            input_=parser_schema,
            parser=None,
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=None
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.DetectorSchema)
        assert len(out_) == 2

    def test_run_detectors_parallel(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=False, do_aggregation=False),
            input_=parser_schema,
            parser=None,
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=None,
            n_workers=2,
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.DetectorSchema)
        assert len(out_) == 2

    def test_run_detectors2aggregator(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=False, do_aggregation=True),
            input_=parser_schema,
            parser=None,
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=DummyAlertAggregator(
                config=DummyAlertAggregatorConfig(buffer_size=2)
            )
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.AggregateSchema)
        assert len(out_) == 1


class TestPipeline:
    @pytest.mark.ignored
    def test_full_pipeline(self) -> None:
        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parser=TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>"
            ),
            detectors=[
                ECVCDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    window_size=10,
                    seed=0,
                    validation_per=0.,
                    threshold_method="mean"
                ),
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                )
            ],
            aggregator=LogIDCountAggegationConfig(max_count=1)
        )

        pipeline = Pipeline(config=config)
        alerts = []
        for parsed_log in From.log(pipeline.parser, in_path=AUDIT_LOG, do_process=True):
            if (alert := pipeline.process(parsed_log)) is not None:
                alerts.extend(alert["logIDs"])

        expected = ['1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867']
        assert set(alerts) == set(expected)

    @pytest.mark.ignored
    def test_full_pipeline_parallel(self) -> None:
        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=3,
            parser=TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>"
            ),
            detectors=[
                ECVCDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    window_size=10,
                    seed=0,
                    validation_per=0.,
                    threshold_method="mean"
                ),
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                )
            ],
            aggregator=LogIDCountAggegationConfig(max_count=1)
        )

        pipeline = Pipeline(config=config)
        alerts = []
        for parsed_log in From.log(pipeline.parser, in_path=AUDIT_LOG, do_process=True):
            if (alert := pipeline.process(parsed_log)) is not None:
                alerts.extend(alert["logIDs"])

        expected = ['1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867']
        assert set(alerts) == set(expected)
