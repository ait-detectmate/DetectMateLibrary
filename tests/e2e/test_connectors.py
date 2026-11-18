"""Chain C9: each component of the audit.log chain (TreeMatcher -> Charset ->
LogIDCount) stores its outputs through a connector, and XSchema.from_id()
must read back exactly what process() returned.

The chain is driven hop by hop, as the service runs it. It runs offline with
the Verification connector (in memory) by default, and against a real
MongoDB / Redis with needs_mongo / needs_redis.
"""
import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegation, LogIDCountAggegationConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcher, TemplateCppTreeMatcherConfig
from tests.support.audit import LOG_FORMAT, TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

STAGES = ("Parser", "Detector", "Aggregator")


@pytest.fixture(params=[
    "Verification",
    pytest.param("Mongo", marks=[pytest.mark.needs_mongo, pytest.mark.slow]),
    pytest.param("Redis", marks=[pytest.mark.needs_redis, pytest.mark.slow]),
])
def connector(request: pytest.FixtureRequest) -> tuple[str, dict[str, str]]:
    """A connector name and the URL each stage stores to."""
    if request.param == "Mongo":
        database = request.getfixturevalue("mongo_db")
        return "Mongo", {stage: database.url(stage) for stage in STAGES}
    if request.param == "Redis":
        databases = request.getfixturevalue("redis_dbs")
        return "Redis", {stage: databases.url(i) for i, stage in enumerate(STAGES)}
    return "Verification", {stage: "memory" for stage in STAGES}


def _restored(schema_class: type[sc.BaseSchema], name: str, url: str, outputs: list) -> list:
    sc.set_connector(name, url=url)
    return [schema_class.from_id(output[output.primary_key]) for output in outputs]


def test_every_stage_reads_back_what_it_returned(connector):
    name, urls = connector
    parser = TemplateCppTreeMatcher(config=TemplateCppTreeMatcherConfig(
        path_templates=AUDIT_TEMPLATES, log_format=LOG_FORMAT,
        connector_name=name, connector_url=urls["Parser"]))
    detector = CharsetDetector(config=CharsetDetectorConfig(
        data_use_configure=TRAIN_UNTIL, data_use_training=1, auto_config=True,
        connector_name=name, connector_url=urls["Detector"]))
    aggregator = LogIDCountAggegation(config=LogIDCountAggegationConfig(
        max_count=1, connector_name=name, connector_url=urls["Aggregator"]))

    parsed = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
    alerts = [alert for alert in map(detector.process, parsed) if alert is not None]
    aggregates = [aggregate for aggregate in map(aggregator.process, alerts) if aggregate is not None]

    assert [aggregate["logIDs"] for aggregate in aggregates] == [
        [log_id] for log_id in ("1859", "1860", "1861", "1862", "1864", "1865", "1866", "1867")]
    assert _restored(sc.ParserSchema, name, urls["Parser"], parsed) == parsed
    assert _restored(sc.DetectorSchema, name, urls["Detector"], alerts) == alerts
    assert _restored(sc.AggregateSchema, name, urls["Aggregator"], aggregates) == aggregates
