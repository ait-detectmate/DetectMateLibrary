"""Tests for detectmatelibrary.detectors.scvs_detector."""
from detectmatelibrary.detectors.scvs_detector import SCVSDetector, SCVSDetectorConfig
from detectmatelibrary.base_detectors import CountVectorDetector
from detectmatelibrary import schemas


import logging

import pytest


class TestSCVSDetector:
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


def test_scvs_is_a_count_vector_detector():
    assert issubclass(SCVSDetector, CountVectorDetector)
    assert SCVSDetectorConfig().session_variable is None and SCVSDetectorConfig().window_size == 10


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
