"""Chain C3 with sessions: the detectors with a session_variable on a log
whose sessions interleave (tests/support/sessions.py).

Each detector learns the training blocks through process() and its config
only, and must raise alerts exactly in the three anomalous blocks; its
alerts must equal its golden file in tests/test_data/golden/sessions/. The
same stream without sessions also alerts on normal blocks, because a window
over the whole stream mixes them.
"""
from pathlib import Path

import pytest

from detectmatelibrary import detectors
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support import sessions

TRAINING = sessions.training_lines()
SESSION_DETECTORS = [
    (detectors.EventSequenceDetector, {
        "method_type": "event_sequence_detector", "auto_config": True,
        "data_use_configure": TRAINING - 1, "data_use_training": 1, "params": {"session_variable": "blk"}}),
    (detectors.ECVCDetector, {
        "method_type": "ecvc_detector", "data_use_training": TRAINING, "params": {
            "session_variable": "blk", "window_size": 3, "seed": 0, "validation_per": 0.0,
            "threshold_method": "mean"}}),
    (detectors.SCVSDetector, {
        "method_type": "scvs_detector", "data_use_training": TRAINING,
        "params": {"session_variable": "blk", "window_size": 3}}),
]


@pytest.fixture(scope="module")
def records() -> list:
    parser = MatcherParser(config={"parsers": {"MatcherParser": {
        "method_type": "matcher_parser", "auto_config": False, "log_format": sessions.LOG_FORMAT,
        "params": {"path_templates": sessions.SESSIONS_TEMPLATES}}}})
    return list(From.log(parser, sessions.SESSIONS_LOG, do_process=True))


def _alerts(cls, entry, records) -> list[list[str]]:
    detector = cls(name=cls.__name__, config={"detectors": {cls.__name__: entry}})
    return [list(output["logIDs"]) for output in map(detector.process, records) if output is not None]


def _blocks(alerts: list[list[str]], records: list) -> set[str]:
    """The blocks the alerts were raised in (by the log that triggered
    them)."""
    block_of = {record["logID"]: record["headerVariables"]["blk"] for record in records}
    return {block_of[alert[-1]] for alert in alerts}


def test_the_log_is_what_the_generator_writes():
    assert Path(sessions.SESSIONS_LOG).read_text() == sessions.generate()
    assert Path(sessions.SESSIONS_TEMPLATES).read_text().splitlines() == sessions.TEMPLATES


@pytest.mark.parametrize("cls, entry", SESSION_DETECTORS, ids=[cls.__name__ for cls, _ in SESSION_DETECTORS])
def test_alerts_fall_in_the_anomalous_blocks_only(cls, entry, records, golden):
    alerts = _alerts(cls, entry, records)

    assert _blocks(alerts, records) == set(sessions.ANOMALOUS)
    golden(f"sessions/{cls.__name__}", {
        "chain": "C3", "dataset": "sessions.log", "training_lines": TRAINING, "detector": cls.__name__,
        "config": entry, "alerts": alerts,
    })


def test_without_sessions_normal_blocks_alert_too(records):
    entry = {"method_type": "event_sequence_detector", "auto_config": False, "data_use_training": TRAINING,
             "params": {"fixed_window_size": 3}}
    blocks = _blocks(_alerts(detectors.EventSequenceDetector, entry, records), records)
    assert blocks - set(sessions.ANOMALOUS)
