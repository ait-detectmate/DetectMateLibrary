"""Chain C7: components set up from config files only.

A Pipeline loaded from a YAML file must give the outputs of the same
pipeline built in Python (chain C2's golden file). A detector configured
with named event IDs and named variables from a named-templates CSV,
resolved by TemplateMatcher.compile_detector_config(), must get the config
the positional names give, and find the labelled su/sudo anomalies.
"""
from pathlib import Path

import yaml

from detectmatelibrary.detectors import NewValueDetector
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.pipeline import Pipeline
from tests.support import golden as golden_files
from tests.support.audit import LOG_FORMAT, TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_NAMED_TEMPLATES, AUDIT_PIPELINE_YAML


def test_yaml_pipeline_gives_the_golden_outputs():
    with open(AUDIT_PIPELINE_YAML) as f:
        config = yaml.safe_load(f)
    params = config["main_pipeline"]["AuditPipeline"]["params"]
    matcher = params["parsers"][0]["parsers"]["TreeMatcher"]["params"]
    matcher["path_templates"] = str(Path(AUDIT_PIPELINE_YAML).parent / matcher["path_templates"])
    pipeline = Pipeline(name="AuditPipeline", config=config)

    outputs = (pipeline.process(log) for log in From.log(pipeline.parsers[0], AUDIT_LOG, do_process=False))
    summaries = [{"type": type(output).__name__, "logIDs": list(output["logIDs"])}
                 for output in outputs if output is not None]
    assert summaries == golden_files.read("pipeline/audit_aggregated")["outputs"]


def _new_value_config(events: dict) -> NewValueDetectorConfig:
    entry = {"method_type": "new_value_detector", "auto_config": False, "data_use_training": TRAIN_UNTIL,
             "events": events}
    return NewValueDetectorConfig.from_dict({"detectors": {"NewValueDetector": entry}}, "NewValueDetector")


def test_named_variables_find_the_su_and_sudo_logins(audit_logs):
    parser = MatcherParser(config={"parsers": {"MatcherParser": {
        "method_type": "matcher_parser", "auto_config": False, "log_format": LOG_FORMAT,
        "params": {"path_templates": AUDIT_NAMED_TEMPLATES}}}})
    named = _new_value_config({"user_session": {"su_and_sudo": {
        "variables": [{"pos": "exe", "name": "exe"}, {"pos": "uid", "name": "uid"}]}}})
    positional = _new_value_config({0: {"su_and_sudo": {
        "variables": [{"pos": 6, "name": "exe"}, {"pos": 1, "name": "uid"}]}}})

    named.events = parser.template_matcher.compile_detector_config(named.events)
    assert named.events.model_dump() == positional.events.model_dump()

    records = list(From.log(parser, AUDIT_LOG, do_process=True))
    # the named wildcards parse as the positional templates do (chain C3's plain parser settings)
    assert [(record["eventID"], list(record["variables"])) for record in records] == \
        [(record["eventID"], list(record["variables"])) for record in audit_logs({"log_format": LOG_FORMAT})]
    detector = NewValueDetector(config=named)
    alerts = [output["logIDs"][-1] for output in map(detector.process, records) if output is not None]
    # uid 33 and /bin/su at 1859-1862, /usr/bin/sudo at 1864-1867 (1863 is another event)
    assert alerts == ["1859", "1860", "1861", "1862", "1864", "1865", "1866", "1867"]
