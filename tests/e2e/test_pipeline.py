"""Chain C2: logs through Pipeline (parsers -> detectors -> aggregator).

The audit.log pipeline uses the setup the repository has always tested:
TreeMatcher, ECVC and Charset, LogIDCount aggregation. ECVC raises nothing in
it because of bug B10 (its configure records are trained on, but
post_train() never runs), so the alerts are Charset's: the 8 labelled
anomalies except 1863. The outputs must equal the golden files in
tests/test_data/golden/pipeline/, whether the pipeline parses or gets parsed
logs and whatever its number of workers.
"""
import logging
from typing import Any

import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.autoparser import AutoParserConfig
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcher, TemplateCppTreeMatcherConfig
from detectmatelibrary.pipeline import Pipeline, PipelineConfig
from tests.support.audit import LOG_FORMAT, TRAIN_UNTIL
from tests.support.databases import MongoDatabase, RedisDatabases
from tests.support.paths import APACHE_LOG, AUDIT_LOG, AUDIT_TEMPLATES

ECVC = {"data_use_configure": TRAIN_UNTIL, "window_size": 10, "seed": 0, "validation_per": 0.0,
        "threshold_method": "mean"}
CHARSET = {"data_use_configure": TRAIN_UNTIL, "data_use_training": 1, "auto_config": True}
AGGREGATOR = {"max_count": 1}
SETUP = {
    "parser": {"TemplateCppTreeMatcher": {"templates": "audit_templates.txt", "log_format": LOG_FORMAT}},
    "detectors": {"ECVCDetector": ECVC, "CharsetDetector": CHARSET},
    "aggregator": {"LogIDCountAggregator": AGGREGATOR},
}


def _audit_parser_config() -> TemplateCppTreeMatcherConfig:
    return TemplateCppTreeMatcherConfig(path_templates=AUDIT_TEMPLATES, log_format=LOG_FORMAT)


def _summary(schema: sc.BaseSchema) -> dict[str, Any]:
    summary = {"type": type(schema).__name__, "logIDs": list(schema["logIDs"])}
    if isinstance(schema, sc.DetectorSchema):
        summary["detectorID"] = schema["detectorID"]
    return summary


def _outputs(pipeline: Pipeline, records: list) -> list:
    """What process() returns for each record that gives output: a summary for
    a single schema, a list of summaries for several."""
    results = (pipeline.process(record) for record in records)
    return [[_summary(item) for item in result] if isinstance(result, list) else _summary(result)
            for result in results if result is not None]


@pytest.mark.parametrize("do_aggregation", [True, False], ids=["aggregated", "detector_outputs"])
@pytest.mark.parametrize("do_parsing, n_workers", [
    (True, 1),
    pytest.param(False, 1, marks=pytest.mark.slow),
    pytest.param(True, 3, marks=pytest.mark.slow),
], ids=["parsing", "parsed_input", "three_workers"])
def test_audit_outputs_match_the_golden_file(do_parsing, n_workers, do_aggregation, golden):
    """One output per anomaly: an aggregate, or a list of the detectors'
    alerts when more than one detector alerts (here only Charset does, so
    a single alert)."""
    pipeline = Pipeline(config=PipelineConfig(
        do_parsing=do_parsing, do_aggregation=do_aggregation, n_workers=n_workers,
        parsers=[_audit_parser_config()] if do_parsing else None,
        detectors=[ECVCDetectorConfig(**ECVC), CharsetDetectorConfig(**CHARSET)],
        aggregator=LogIDCountAggegationConfig(**AGGREGATOR) if do_aggregation else None,
    ))
    parser = TemplateCppTreeMatcher(config=_audit_parser_config())
    records = list(From.log(parser, in_path=AUDIT_LOG, do_process=not do_parsing))

    name = "aggregated" if do_aggregation else "detector_outputs"
    golden(f"pipeline/audit_{name}", {
        "chain": "C2", "dataset": "audit.log", "setup": SETUP, "aggregated": do_aggregation,
        "outputs": _outputs(pipeline, records),
    })


@pytest.mark.slow
def test_two_sources_reach_only_their_own_detector(golden):
    """Audit logs go through TreeMatcher, Apache logs through AutoParser; each
    Charset detector listens to one parser.

    The Apache detector is configured on its first 10 lines only, so it
    alerts on most later ones.
    """
    pipeline = Pipeline(config=PipelineConfig(
        do_parsing=True, do_aggregation=False,
        parsers=[
            TemplateCppTreeMatcherConfig(path_templates=AUDIT_TEMPLATES, log_format=LOG_FORMAT,
                                         log_source="Audit_logs"),
            AutoParserConfig(fix_type="Apache", log_source="Apache_logs", data_use_training=1),
        ],
        detectors=[
            CharsetDetectorConfig(**CHARSET, parser="TreeMatcher_from_Audit_logs"),
            CharsetDetectorConfig(data_use_configure=10, data_use_training=1, auto_config=True,
                                  parser="AutoParser_from_Apache_logs"),
        ],
    ))
    records = []
    for source, path in (("Apache", APACHE_LOG), ("Audit", AUDIT_LOG)):
        for log in From.log(pipeline.parsers[0], path, do_process=False):
            log["logID"], log["logSource"] = f"{source}_{log['logID']}", f"{source}_logs"
            records.append(log)

    own_detector = {"Audit": "CharsetDetector_from_TreeMatcher_from_Audit_logs",
                    "Apache": "CharsetDetector_from_AutoParser_from_Apache_logs"}
    alerts = _outputs(pipeline, records)
    assert all(alert["detectorID"] == own_detector[alert["logIDs"][0].split("_")[0]] for alert in alerts)
    golden("pipeline/audit_and_apache", {
        "chain": "C2", "datasets": ["apache.log", "audit.log"],
        "alerts": {source: [alert["logIDs"][0] for alert in alerts if alert["logIDs"][0].startswith(source)]
                   for source in ("Audit", "Apache")},
    })


class TestPipelineWithDatabases:
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
