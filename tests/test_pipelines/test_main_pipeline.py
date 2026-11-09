from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL, APACHE_LOG

from detectmatelibrary.pipeline import PipelineConfig, _run_pipeline, Pipeline

from detectmatelibrary._testutils.dummy_parser import DummyParser, DummyParserConfig
from detectmatelibrary._testutils.dummy_detector import DummyDetectorConfig
from detectmatelibrary._testutils.dummy_alert_aggregator import (
    DummyAlertAggregator, DummyAlertAggregatorConfig
)

from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc

from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig

from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig
from detectmatelibrary.parsers.autoparser import AutoParserConfig

from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig

import logging
import pymongo
import redis

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


class TestPipeline:
    @pytest.mark.ignored
    def test_full_pipeline(self) -> None:
        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parsers=[TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>"
            )],
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
        for parsed_log in From.log(pipeline.parsers[0], in_path=AUDIT_LOG, do_process=False):
            if (alert := pipeline.process(parsed_log)) is not None:
                alerts.extend(alert["logIDs"])

        expected = ['1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867']
        assert set(alerts) == set(expected)

    @pytest.mark.ignored
    def test_full_pipeline_two_sources(self) -> None:
        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parsers=[
                TemplateCppTreeMatcherConfig(
                    path_templates=AUDIT_TEMPLATES,
                    log_format="type=<Type> msg=audit(<Time>): <Content>",
                    log_source="Audit_logs",
                ),
                AutoParserConfig(
                    fix_type="Apache",
                    log_source="Apache_logs",
                    data_use_training=1,
                ),
            ],
            detectors=[
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                    parser="TreeMatcher_from_Audit_logs"
                ),
                CharsetDetectorConfig(
                    data_use_configure=10,
                    data_use_training=1,
                    auto_config=True,
                    parser="AutoParser_from_Apache_logs",
                )
            ],
            aggregator=LogIDCountAggegationConfig(max_count=1)
        )
        pipeline = Pipeline(config=config)

        all_logs = []
        for apache_log in From.log(pipeline.parsers[0], APACHE_LOG, do_process=False):
            apache_log["logID"] = "Apache_" + apache_log["logID"]
            apache_log["logSource"] = "Apache_logs"
            all_logs.append(apache_log)

        for audit_log in From.log(pipeline.parsers[0], AUDIT_LOG, do_process=False):
            audit_log["logID"] = "Audit_" + audit_log["logID"]
            audit_log["logSource"] = "Audit_logs"
            all_logs.append(audit_log)

        alerts_audit, alerts_apache = False, False
        for logs in all_logs:
            if (alert := pipeline.process(logs)) is not None:
                alerts_audit = alerts_audit if alerts_audit else "Audit" in alert["logIDs"][0]
                alerts_apache = alerts_apache if alerts_apache else "Apache" in alert["logIDs"][0]

        assert alerts_audit
        assert alerts_apache

    @pytest.mark.ignored
    def test_full_pipeline_parallel(self) -> None:
        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=3,
            parsers=[TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>"
            )],
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
        for parsed_log in From.log(pipeline.parsers[0], in_path=AUDIT_LOG, do_process=False):
            if (alert := pipeline.process(parsed_log)) is not None:
                alerts.extend(alert["logIDs"])

        expected = ['1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867']
        assert set(alerts) == set(expected)

    @pytest.mark.ignored_mongo
    @pytest.mark.ignored
    def test_full_pipeline_mongo(self) -> None:
        logging.getLogger().setLevel(logging.CRITICAL)
        client = pymongo.MongoClient("mongodb://localhost:27017")
        for col_n in ["Parser", "Detector", "Aggregator"]:
            col = client["FullPipeline"][col_n]
            col.delete_many({})
        client.close()

        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parsers=[TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>",
                connector_name="Mongo",
                connector_url="mongodb://localhost:27017/FullPipeline/Parser",
            )],
            detectors=[
                ECVCDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    window_size=10,
                    seed=0,
                    validation_per=0.,
                    threshold_method="mean",
                    connector_name="Mongo",
                    connector_url="mongodb://localhost:27017/FullPipeline/Detector",
                ),
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                    connector_name="Mongo",
                    connector_url="mongodb://localhost:27017/FullPipeline/Detector",
                )
            ],
            aggregator=LogIDCountAggegationConfig(
                max_count=1,
                connector_name="Mongo",
                connector_url="mongodb://localhost:27017/FullPipeline/Aggregator",
            )
        )

        pipeline = Pipeline(config=config)
        for parsed_log in From.log(pipeline.parsers[0], in_path=AUDIT_LOG, do_process=False):
            if pipeline.process(parsed_log) is not None:
                break

        sc.set_connector("Mongo", url="mongodb://localhost:27017/FullPipeline/Parser")
        assert sc.ParserSchema.from_id("TreeMatcher_10")["log"] != ""

        sc.set_connector("Mongo", url="mongodb://localhost:27017/FullPipeline/Detector")
        assert sc.DetectorSchema.from_id("CharsetDetector_10")["score"] != 0.0

        sc.set_connector("Mongo", url="mongodb://localhost:27017/FullPipeline/Aggregator")
        assert sc.AggregateSchema.from_id("LogIDCountAggregator_10")["logIDs"] != ""

    @pytest.mark.ignored_redis
    @pytest.mark.ignored
    def test_full_pipeline_redis(self) -> None:
        logging.getLogger().setLevel(logging.CRITICAL)
        for i in range(3):
            client = redis.Redis(host="localhost", port=6379, db=i)
            client.flushdb()
            client.close()

        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parsers=[TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>",
                connector_name="Redis",
                connector_url="http://localhost:6379:0",
            )],
            detectors=[
                ECVCDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    window_size=10,
                    seed=0,
                    validation_per=0.,
                    threshold_method="mean",
                    connector_name="Redis",
                    connector_url="http://localhost:6379:1",
                ),
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                    connector_name="Redis",
                    connector_url="http://localhost:6379:1",
                )
            ],
            aggregator=LogIDCountAggegationConfig(
                max_count=1,
                connector_name="Redis",
                connector_url="http://localhost:6379:2",
            )
        )

        pipeline = Pipeline(config=config)
        for parsed_log in From.log(pipeline.parsers, in_path=AUDIT_LOG, do_process=False):
            if pipeline.process(parsed_log) is not None:
                break

        sc.set_connector("Redis", url="http://localhost:6379:0")
        assert sc.ParserSchema.from_id("TreeMatcher_10")["log"] != ""

        sc.set_connector("Redis", url="http://localhost:6379:1")
        assert sc.DetectorSchema.from_id("CharsetDetector_10")["score"] != 0.0

        sc.set_connector("Redis", url="http://localhost:6379:2")
        assert sc.AggregateSchema.from_id("LogIDCountAggregator_10")["logIDs"] != ""
