"""Chain C2: raw logs through Pipeline (parsers -> detectors -> aggregator)."""
from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES, APACHE_LOG
from detectmatelibrary.pipeline import PipelineConfig, Pipeline
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as sc
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig
from detectmatelibrary.parsers.autoparser import AutoParserConfig
from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig
import logging
import pytest
from tests.support.databases import MongoDatabase, RedisDatabases


class TestPipeline:
    @pytest.mark.slow
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

    @pytest.mark.slow
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

    @pytest.mark.slow
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

    @pytest.mark.needs_mongo
    @pytest.mark.slow
    def test_full_pipeline_mongo(self, mongo_db: MongoDatabase) -> None:
        logging.getLogger().setLevel(logging.CRITICAL)

        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parsers=[TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>",
                connector_name="Mongo",
                connector_url=mongo_db.url("Parser"),
            )],
            detectors=[
                ECVCDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    window_size=10,
                    seed=0,
                    validation_per=0.,
                    threshold_method="mean",
                    connector_name="Mongo",
                    connector_url=mongo_db.url("Detector"),
                ),
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                    connector_name="Mongo",
                    connector_url=mongo_db.url("Detector"),
                )
            ],
            aggregator=LogIDCountAggegationConfig(
                max_count=1,
                connector_name="Mongo",
                connector_url=mongo_db.url("Aggregator"),
            )
        )

        pipeline = Pipeline(config=config)
        for parsed_log in From.log(pipeline.parsers[0], in_path=AUDIT_LOG, do_process=False):
            if pipeline.process(parsed_log) is not None:
                break

        sc.set_connector("Mongo", url=mongo_db.url("Parser"))
        assert sc.ParserSchema.from_id("TreeMatcher_10")["log"] != ""

        sc.set_connector("Mongo", url=mongo_db.url("Detector"))
        assert sc.DetectorSchema.from_id("CharsetDetector_10")["score"] != 0.0

        sc.set_connector("Mongo", url=mongo_db.url("Aggregator"))
        assert sc.AggregateSchema.from_id("LogIDCountAggregator_10")["logIDs"] != ""

    @pytest.mark.needs_redis
    @pytest.mark.slow
    def test_full_pipeline_redis(self, redis_dbs: RedisDatabases) -> None:
        logging.getLogger().setLevel(logging.CRITICAL)

        config = PipelineConfig(
            do_parsing=True,
            do_aggregation=True,
            n_workers=1,
            parsers=[TemplateCppTreeMatcherConfig(
                path_templates=AUDIT_TEMPLATES,
                log_format="type=<Type> msg=audit(<Time>): <Content>",
                connector_name="Redis",
                connector_url=redis_dbs.url(0),
            )],
            detectors=[
                ECVCDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    window_size=10,
                    seed=0,
                    validation_per=0.,
                    threshold_method="mean",
                    connector_name="Redis",
                    connector_url=redis_dbs.url(1),
                ),
                CharsetDetectorConfig(
                    data_use_configure=TRAIN_UNTIL,
                    data_use_training=1,
                    auto_config=True,
                    connector_name="Redis",
                    connector_url=redis_dbs.url(1),
                )
            ],
            aggregator=LogIDCountAggegationConfig(
                max_count=1,
                connector_name="Redis",
                connector_url=redis_dbs.url(2),
            )
        )

        pipeline = Pipeline(config=config)
        for parsed_log in From.log(pipeline.parsers[0], in_path=AUDIT_LOG, do_process=False):
            if pipeline.process(parsed_log) is not None:
                break

        sc.set_connector("Redis", url=redis_dbs.url(0))
        assert sc.ParserSchema.from_id("TreeMatcher_10")["log"] != ""

        sc.set_connector("Redis", url=redis_dbs.url(1))
        assert sc.DetectorSchema.from_id("CharsetDetector_10")["score"] != 0.0

        sc.set_connector("Redis", url=redis_dbs.url(2))
        assert sc.AggregateSchema.from_id("LogIDCountAggregator_10")["logIDs"] != ""
