
from detectmatelibrary.detectors.scvs_detector import SCVSDetector, SCVSDetectorConfig
from detectmatelibrary.base_detectors import CountVectorDetector, SessionWindows
from detectmatelibrary.utils.sequence_encoding import count_events, encode_count_vec
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from detectmatelibrary import schemas

from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

import logging

import pytest


class TestSCVSDetector:

    def test_window_size(self):
        ecvc = SCVSDetector(config=SCVSDetectorConfig(window_size=10))
        assert ecvc.get_window_size() == 10

        ecvc = SCVSDetector(config=SCVSDetectorConfig(window_size=7))
        assert ecvc.get_window_size() == 7

    def test_scvs(self):
        config = {
            "detectors": {
                "SCVSDetector": {
                    "method_type": "scvs_detector",
                    "window_size": 3,
                    "data_use_training": 30,
                }
            }
        }

        scvs = SCVSDetector(config=config)

        input_ = []
        for _ in range(10):
            input_.extend([schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]])

        for in_ in input_:
            scvs.process(in_)
        assert scvs.get_state() == "Default"

        for in_ in input_[5:15]:
            alert = scvs.process(in_)
        assert alert is None

        for in_ in [schemas.ParserSchema({"eventID": i}) for i in [4, 4, 4, 4, 4, 4, 1, 0, 1, 1]]:
            alert = scvs.process(in_)
        assert alert is not None


PIPELINE_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": AUDIT_TEMPLATES,
            },
        }
    },
    "detectors": {
        "SCVSDetector": {
            "method_type": "scvs_detector",
            "window_size": 10,
            "data_use_training": TRAIN_UNTIL,
        },
        "SCVSDetector_fed": {
            "method_type": "scvs_detector",
            "window_size": 10,
            "data_use_training": TRAIN_UNTIL,
            "allow_fed": True,
        }
    }
}


class TestSCVSDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.slow
    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector = SCVSDetector(config=PIPELINE_CONFIG)

        detected_ids = set()
        for parsed_log in From.log(parser, in_path=AUDIT_LOG, do_process=True):
            alert = detector.process(parsed_log)
            if detector.get_state() == "Default" and alert is not None:
                detected_ids.update(set([log_id for log_id in alert["logIDs"]]))

        for log_id in {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}:
            assert log_id in detected_ids

    @pytest.mark.slow
    def test_audit_log_anomalie_binary(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector1 = SCVSDetector("SCVSDetector_fed", config=PIPELINE_CONFIG)
        detector2 = SCVSDetector("SCVSDetector_fed", config=PIPELINE_CONFIG)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs[:TRAIN_UNTIL]:
            detector1.process(log)

        binary = detector1.to_binary()
        detector2 = detector2.from_binary(binary)

        assert detector2.persistency.events_seen == detector1.persistency.events_seen
        assert len(detector2.persistency.events_seen) > 0

    @pytest.mark.slow
    def test_audit_log_anomalie_fed(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector1 = SCVSDetector("SCVSDetector_fed", config=PIPELINE_CONFIG)
        detector2 = SCVSDetector("SCVSDetector_fed", config=PIPELINE_CONFIG)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs[:TRAIN_UNTIL]:
            detector1.process(log)

        (detector1 + detector2).aggregate()
        assert detector2.persistency.events_seen == detector1.persistency.events_seen
        assert len(detector2.persistency.events_seen) > 0


def _window(event_ids):
    return [schemas.ParserSchema({"eventID": i}) for i in event_ids]


def _fed_detector(window_size):
    return SCVSDetector(config=SCVSDetectorConfig(window_size=window_size, allow_fed=True))


class TestSCVSDetectorRestoredState:
    """State counted over another window size warns on every restore path."""

    def test_warns_after_from_binary(self, tmp_path, monkeypatch, caplog):
        monkeypatch.chdir(tmp_path)  # the slow store writes .temp/ CSVs here
        trained = _fed_detector(3)
        trained.train(_window([0, 1, 4]))

        with caplog.at_level(logging.WARNING):
            _fed_detector(4).from_binary(trained.to_binary())

        assert any("window_size 3" in r.message for r in caplog.records)

    def test_warns_after_aggregate(self, tmp_path, monkeypatch, caplog):
        monkeypatch.chdir(tmp_path)
        trained = _fed_detector(3)
        trained.train(_window([0, 1, 4]))
        receiver = _fed_detector(4)

        with caplog.at_level(logging.WARNING):
            (receiver + trained).aggregate()

        assert any("window_size 3" in r.message for r in caplog.records)

    def test_finalize_federation_removes_the_slow_table(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        detector = _fed_detector(3)
        detector.train(_window([0, 1, 4]))
        assert (tmp_path / ".temp").exists()

        detector.finalize_federation()

        assert not (tmp_path / ".temp").exists()


def _record(event, session):
    return schemas.ParserSchema({"eventID": event, "headerVariables": {"blk": session}})


def _counts(*windows):
    """The persistency keys of the count vectors of these windows (window_size
    2)."""
    return {encode_count_vec(2, count_events(w)) for w in windows}


# Two interleaved sessions, a: 1 3 5 and b: 2 4, and the window (size 2) ending at each event.
STREAM = [("a", 1), ("b", 2), ("a", 3), ("b", 4), ("a", 5)]
WINDOWS = [(1,), (2,), (1, 3), (2, 4), (3, 5)]


def _session_detector(**config):
    return SCVSDetector(config=SCVSDetectorConfig(window_size=2, session_variable="blk", **config))


def test_scvs_is_a_count_vector_detector():
    assert issubclass(SCVSDetector, CountVectorDetector)
    assert SCVSDetectorConfig().session_variable is None and SCVSDetectorConfig().window_size == 10


class TestSCVSSessionWindows:
    """With session_variable, an event's window holds the events before it in
    its own session."""

    def test_windows_never_mix_sessions(self):
        windows = SessionWindows(size=2)
        assert [windows.add(s, e) for s, e in STREAM] == WINDOWS

    def test_training_counts_the_windows_of_each_session(self):
        detector = _session_detector(data_use_training=len(STREAM))
        for s, e in STREAM:
            detector.process(_record(e, s))
        assert set(detector.persistency.get_events_seen()) == _counts(*WINDOWS)

    def test_each_phase_sees_each_event_once(self):
        # Configure records are replayed into train() after the configure phase: the windows
        # must not count an event twice or lose one.
        detector = _session_detector(data_use_configure=2, data_use_training=1)
        for s, e in STREAM:
            detector.process(_record(e, s))
        assert set(detector.persistency.get_events_seen()) == _counts(*WINDOWS[:3])

    def test_detection_scores_the_window_of_the_events_own_session(self):
        # Training sees one session alternating 1 and 2. Two sessions doing the same, interleaved,
        # raise nothing (a stream window would count 1 1 and 2 2); a session starting with 2 does.
        detector = _session_detector(data_use_training=6)
        alerts = [detector.process(_record(e, "t")) for e in (1, 2, 1, 2, 1, 2)]
        for s, e in [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 1), ("b", 1)]:
            alerts.append(detector.process(_record(e, s)))
        alerts.append(detector.process(_record(2, "c")))
        assert [a is not None for a in alerts] == [False] * 12 + [True]
        assert alerts[-1]["logIDs"] == [str(_record(2, "c")["logID"])]

    def test_missing_session_variable_raises(self):
        detector = _session_detector(data_use_training=1)
        with pytest.raises(ValueError, match="blk"):
            detector.process(schemas.ParserSchema({"eventID": 1}))


WINDOW_SIZE = 4


# Distinct count vectors over EventIDs 0/1/4, each WINDOW_SIZE events long.
TRAIN_WINDOWS = [[0, 1, 4, 0], [1, 1, 0, 0], [4, 0, 1, 1], [0, 0, 4, 4]]


class TestSCVSDetectorPersist:
    def test_import_state_warns_on_window_size_mismatch(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        det1 = SCVSDetector(
            name="SCVS_WSSrc",
            config=SCVSDetectorConfig(auto_config=False, window_size=WINDOW_SIZE),
        )
        for window in TRAIN_WINDOWS:
            det1.train(_window(window))
        state = det1.export_state()

        det2 = SCVSDetector(
            name="SCVS_WSDst",
            config=SCVSDetectorConfig(auto_config=False, window_size=WINDOW_SIZE + 2),
        )
        with caplog.at_level(logging.WARNING):
            det2.import_state(state)
        assert any("window_size" in r.message for r in caplog.records)
