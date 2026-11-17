"""Tests for detectmatelibrary.pipeline."""
from detectmatelibrary.pipeline import PipelineConfig, _run_pipeline

from detectmatelibrary._testutils.dummy_parser import DummyParser, DummyParserConfig
from detectmatelibrary._testutils.dummy_detector import DummyDetectorConfig
from detectmatelibrary._testutils.dummy_alert_aggregator import (
    DummyAlertAggregator, DummyAlertAggregatorConfig
)

import detectmatelibrary.schemas as sc

from detectmatelibrary.common.detector import CoreDetector


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


log_schema = sc.LogSchema({"logID": "1", "log": "hello", "logSource": "A"})
log_schema_2 = sc.LogSchema({"logID": "2", "log": "ciao", "logSource": "B"})

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
            parsers=[DummyParser()],
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=None
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.DetectorSchema)
        assert len(out_) == 2

    def test_run_parsers2detectors(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=False),
            input_=log_schema,
            parsers=[
                DummyParser(config=DummyParserConfig(log_source="A")),
                DummyParser(config=DummyParserConfig(log_source="B"))
            ],
            detectors=[
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_A")),
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_B"))
            ],
            alert_aggreator=None
        )
        assert out_[0]["logIDs"] == ["1"]
        assert out_[0]["detectorID"] == "DummyDetector_from_DummyParser_from_A"
        assert len(out_) == 1

        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=False),
            input_=log_schema_2,
            parsers=[
                DummyParser(config=DummyParserConfig(log_source="A")),
                DummyParser(config=DummyParserConfig(log_source="B"))
            ],
            detectors=[
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_A")),
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_B"))
            ],
            alert_aggreator=None
        )
        assert out_[0]["logIDs"] == ["2"]
        assert out_[0]["detectorID"] == "DummyDetector_from_DummyParser_from_B"
        assert len(out_) == 1

    def test_run_parser2aggregator(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=True),
            input_=log_schema,
            parsers=[DummyParser()],
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=DummyAlertAggregator(
                config=DummyAlertAggregatorConfig(buffer_size=2)
            )
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.AggregateSchema)
        assert len(out_) == 1

    def test_run_parsers2aggregator(self) -> None:
        alert_aggregator = DummyAlertAggregator(
            config=DummyAlertAggregatorConfig(buffer_size=2)
        )

        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=True),
            input_=log_schema,
            parsers=[
                DummyParser(config=DummyParserConfig(log_source="A")),
                DummyParser(config=DummyParserConfig(log_source="B"))
            ],
            detectors=[
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_A")),
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_B"))
            ],
            alert_aggreator=alert_aggregator
        )
        assert out_ == []

        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=True, do_aggregation=True),
            input_=log_schema_2,
            parsers=[
                DummyParser(config=DummyParserConfig(log_source="A")),
                DummyParser(config=DummyParserConfig(log_source="B"))
            ],
            detectors=[
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_A")),
                AlwayAlert(config=DummyDetectorConfig(parser="DummyParser_from_B"))
            ],
            alert_aggreator=alert_aggregator
        )
        assert len(out_) == 1
        assert set(out_[0]["logIDs"]) == {"1", "2"}

    def test_run_detectors_only(self) -> None:
        out_ = _run_pipeline(
            config=PipelineConfig(do_parsing=False, do_aggregation=False),
            input_=parser_schema,
            parsers=None,
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
            parsers=None,
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
            parsers=None,
            detectors=[AlwayAlert(), AlwayAlert()],
            alert_aggreator=DummyAlertAggregator(
                config=DummyAlertAggregatorConfig(buffer_size=2)
            )
        )

        assert isinstance(out_, list)
        assert isinstance(out_[0], sc.AggregateSchema)
        assert len(out_) == 1
