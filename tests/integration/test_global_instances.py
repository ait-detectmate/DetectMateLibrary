"""Global instances (YAML `global:`): header variables tracked across all event
IDs under GLOBAL_EVENT_ID, from parsing to alerts.

Each detector trains on the first 1,800 lines of audit.log and checks the
rest. The expected sets are what the detectors report today, checked
against the data: NEW_TYPES are the only three logs of the Types CRED_REFR,
USER_AUTH and USER_CMD, which never occur in training.
"""
import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary import detectors
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

PARSER_CONFIG = {"parsers": {"MatcherParser": {
    "method_type": "matcher_parser",
    "auto_config": False,
    "log_format": "type=<Type> msg=audit(<Time>:<Line>): <Content>",
    "time_format": None,
    "params": {"remove_spaces": True, "remove_punctuation": True, "lowercase": True,
               "path_templates": AUDIT_TEMPLATES},
}}}

NEW_TYPES = {"1859", "1863", "1864"}
_B9 = pytest.mark.xfail(strict=True, raises=AssertionError,
                        reason="B9: NewEventDetector with a global instance alerts on every log")

CASES = [
    pytest.param(detectors.NewValueDetector, "Type", {}, NEW_TYPES, id="NewValueDetector"),
    pytest.param(detectors.CharsetDetector, "Type", {}, NEW_TYPES, id="CharsetDetector"),
    # at prob_thresh 0.2 only one of the new Types has improbable letter pairs
    pytest.param(detectors.BigramFrequencyDetector, "Type", {"prob_thresh": 0.2}, {"1864"},
                 id="BigramFrequencyDetector"),
    # every timestamp after line 1801 is later than the learned range
    pytest.param(detectors.ValueRangeDetector, "Time", {"params": {"ignore_non_numerical_val": True}},
                 {str(i) for i in range(1801, 2316)}, id="ValueRangeDetector"),
    # the same logs as without a global instance: the one event ID never seen in training
    pytest.param(detectors.NewEventDetector, "Type", {}, {"1863"}, id="NewEventDetector", marks=_B9),
]


@pytest.fixture(scope="module")
def audit_logs() -> list:
    return list(From.log(MatcherParser(config=PARSER_CONFIG), in_path=AUDIT_LOG, do_process=True))


@pytest.mark.parametrize("detector_cls, variable, settings, expected", CASES)
def test_global_instance_flags_the_expected_logs(detector_cls, variable, settings, expected, audit_logs):
    name = detector_cls.__name__
    detector = detector_cls(name=name, config={"detectors": {name: {
        "method_type": detector_cls().config.method_type,
        "auto_config": False,
        "global": {"test": {"header_variables": [{"pos": variable}]}},
        **settings,
    }}})
    logs = [log.copy() for log in audit_logs]

    for log in logs[:TRAIN_UNTIL]:
        detector.train(log)
    assert GLOBAL_EVENT_ID in detector.persistency.get_events_seen()

    detected = set()
    for log in logs[TRAIN_UNTIL:]:
        alert = sc.DetectorSchema()
        if detector.detect(log, output_=alert):
            assert all(key.startswith("Global -") for key in alert["alertDetails"])
            detected.add(log["logID"])
    assert detected == expected
