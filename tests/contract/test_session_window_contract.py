"""Contract of the detectors with a session_variable: each event is judged
in the window of its own session.

Runs for SESSION_DETECTORS in tests/contract/registry.py. Each detector
learns its case's training events as one session (1 2 1 2 1 2 for the
sequence and count-vector detectors); two sessions doing the same,
interleaved, must raise nothing, although a window over the whole stream
would see 1 1 and 2 2. Which windows a model sees is checked at the base level with
recording models (unit/base_detectors/test_count_vector_detector.py,
test_deeplearning_detector.py) and per detector in unit/detectors/.
"""
import pytest

from detectmatelibrary import detectors
from tests.contract.registry import DETECTORS, SESSION_DETECTORS, cases, parsed_log, session_log

INTERLEAVED = [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 1), ("b", 1)]
# DeepLog / LogBERT detections depend on the trained model, so they only get
# the checks that don't compare alerts with a fixed expectation
MODEL_BASED = {detectors.DeeplogDetector, detectors.LogBertDetector}
FIXED_RULE = [case for case in SESSION_DETECTORS if case.cls not in MODEL_BASED]


def _records(pairs: list[tuple[str, int]], start: int = 0) -> list:
    return [session_log(start + i, session, event_id) for i, (session, event_id) in enumerate(pairs)]


def _train_records(case) -> list:
    """The case's training events, as one session."""
    return _records([("t", record["eventID"]) for record in case.train()])


def _session_detector(case, **params):
    """A detector that learned its training data as one session."""
    train = _train_records(case)
    detector = case.build(session_variable="blk", data_use_training=len(train), **params)
    for record in train:
        detector.process(record)
    return detector


def test_every_detector_with_sessions_is_registered():
    with_sessions = {case.cls for case in DETECTORS
                     if "session_variable" in type(case.cls().config).model_fields}
    assert with_sessions == {case.cls for case in SESSION_DETECTORS}


@pytest.mark.parametrize("case", cases(SESSION_DETECTORS))
def test_session_variable_is_off_by_default(case):
    assert case.cls().config.session_variable is None


@pytest.mark.parametrize("case", cases(SESSION_DETECTORS))
def test_a_log_without_the_session_variable_raises(case):
    detector = case.build(session_variable="blk")
    with pytest.raises(ValueError, match="blk"):
        detector.process(parsed_log(0))


@pytest.mark.parametrize("case", cases(FIXED_RULE))
class TestSessionDetection:
    def test_interleaved_known_sessions_raise_nothing(self, case):
        detector = _session_detector(case)
        assert [detector.process(record) for record in _records(INTERLEAVED, start=10)] == [None] * 6

    def test_a_session_with_an_unseen_start_alerts_on_that_event(self, case):
        """No learned session starts with 2; the alert names only that
        event."""
        detector = _session_detector(case)
        alert = detector.process(session_log(30, "c", 2))

        assert alert is not None
        assert list(alert["logIDs"]) == ["30"]

    def test_without_sessions_the_same_stream_alerts(self, case):
        """The reference: windows over the whole stream mix the sessions."""
        detector = case.trained()
        alerts = [detector.process(record) for record in _records(INTERLEAVED, start=10)]
        assert any(alert is not None for alert in alerts)


@pytest.mark.parametrize("case", cases(SESSION_DETECTORS, trains=True))
def test_configure_replay_neither_drops_nor_repeats_events(case):
    """Configure records are replayed into training afterwards: a detector
    with a configure phase must learn exactly what one without it learns."""
    train = _train_records(case)
    with_configure = case.build(session_variable="blk", data_use_configure=2,
                                data_use_training=len(train) - 2)
    without = case.build(session_variable="blk", data_use_training=len(train))
    for record in train:
        with_configure.process(record)
        without.process(record)

    probes = _records([*INTERLEAVED, ("c", 2), ("c", 1), ("d", 1), ("d", 1)], start=40)
    scores = [[None if out is None else out["score"] for out in map(detector.process, probes)]
              for detector in (with_configure, without)]
    assert scores[0] == scores[1]
