"""Tests for detectmatelibrary.pipeline."""
from detectmatelibrary.pipeline import Pipeline, PipelineConfig, _run_pipeline
from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregationConfig
from detectmatelibrary.detectors.random_detector import RandomDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetectorConfig

from detectmatelibrary._testutils.dummy_parser import DummyParser, DummyParserConfig
from detectmatelibrary._testutils.dummy_detector import DummyDetectorConfig
from detectmatelibrary._testutils.dummy_alert_aggregator import (
    DummyAlertAggregator, DummyAlertAggregatorConfig
)

import detectmatelibrary.schemas as sc
import pytest

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


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="B2: Pipeline.output_schema is DetectorSchema with aggregation and vice versa")
@pytest.mark.parametrize("do_aggregation, expected", [
    (True, sc.AggregateSchema), (False, sc.DetectorSchema),
], ids=["True", "False"])
def test_output_schema_matches_aggregation(do_aggregation, expected):
    # Pipeline builds its components with selectComponent, which only finds package classes
    config = PipelineConfig(
        do_parsing=False, do_aggregation=do_aggregation, detectors=[RandomDetectorConfig()],
        aggregator=BasicConcatAggregationConfig() if do_aggregation else None,
    )
    assert Pipeline(config=config).output_schema is expected


# RuleDetector's default rules alert on a log whose template was not found. Loading it
# changes RuleDetector's shared default config (bug B1, through selectComponent); the
# guard in tests/conftest.py restores it and lists these tests at the end of the run.
NOT_FOUND = sc.ParserSchema({"logID": "1", "eventID": -1, "template": "<Not Found>", "log": "x"})
FOUND = sc.ParserSchema({"logID": "2", "eventID": 1, "template": "a <*>", "log": "a b"})


def _rule_pipeline(n_detectors: int) -> Pipeline:
    return Pipeline(config=PipelineConfig(
        do_parsing=False, do_aggregation=False, detectors=[RuleDetectorConfig() for _ in range(n_detectors)]))


class TestPipelineProcess:
    def test_no_alert_gives_none(self):
        assert _rule_pipeline(1).process(FOUND) is None

    def test_one_alert_gives_the_alert_itself(self):
        assert isinstance(_rule_pipeline(1).process(NOT_FOUND), sc.DetectorSchema)

    def test_several_alerts_give_a_list(self):
        alerts = _rule_pipeline(2).process(NOT_FOUND)
        assert [type(alert) for alert in alerts] == [sc.DetectorSchema, sc.DetectorSchema]

    def test_bytes_in_give_bytes_out(self):
        output = _rule_pipeline(1).process(NOT_FOUND.serialize())
        alert = sc.DetectorSchema()
        alert.deserialize(output)
        assert list(alert["logIDs"]) == ["1"]

    def test_a_yaml_dict_is_read_under_the_pipeline_name(self):
        pipeline = Pipeline(name="Rules", config={"main_pipeline": {"Rules": {
            "method_type": "pipeline",
            "params": {"do_parsing": False, "do_aggregation": False,
                       "detectors": [{"detectors": {"RuleDetector": {"method_type": "rule_detector"}}}]},
        }}})
        assert isinstance(pipeline.process(NOT_FOUND), sc.DetectorSchema)
