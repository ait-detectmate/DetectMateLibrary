
from detectmatelibrary.detectors.ecvc_detector import ECVCOp, ECVCDetectorConfig, ECVCDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from detectmatelibrary import schemas

from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

import logging

import numpy as np
import pytest


class TestECVCOP:
    def test_build_count_vec(self):
        input_ = [
            schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]
        ]
        expected = tuple([2, 1, 0, 0, 1])

        assert ECVCOp.build_count_vec(input_) == expected

    def test_build_one_vec(self):
        input_ = [
            schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]
        ]

        expected = np.array([2, 1, 0, 0, 1, 0, 0, 0])
        assert np.array_equal(ECVCOp.build_one_vec(input_, 8), expected)

        expected = np.array([2, 1, 0, 0, 1])
        assert np.array_equal(ECVCOp.build_one_vec(input_, 3), expected)

    def test_init_count_matrix(self):
        input_ = [
            (1, 0, 2, 1), (1, 2, 1), (0, 1, 4)
        ]
        expected = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])

        assert np.array_equal(ECVCOp.init_count_matrix(input_), expected)

    def test_calculate_score(self):
        input_ = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])
        y = np.array([0, 1, 4, 0, 0])

        assert 0.0 == ECVCOp.calculate_score(y, matrix=input_)

        input_ = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])
        y = np.array([0, 1, 4, 0])

        assert 0.0 == ECVCOp.calculate_score(y, matrix=input_)

    def test_calculate_score_matches_the_row_loop(self):
        rng = np.random.default_rng(0)
        for rows, cols, extra in [(1, 3, 0), (5, 4, 2), (200, 30, 0), (200, 30, 5)]:
            matrix = rng.integers(0, 4, (rows, cols)).astype(float)
            for _ in range(20):
                y = rng.integers(0, 4, cols + extra).astype(float)
                assert ECVCOp.calculate_score(y, matrix) == _row_loop_score(y, matrix)

    def test_calculate_score_without_rows_is_inf(self):
        assert ECVCOp.calculate_score(np.array([1., 2.]), matrix=np.zeros((0, 2))) == np.inf

    def test_calculate_threshol(self):
        matrix = np.array([
            [1, 0, 2, 1], [1, 2, 1, 0], [0, 1, 4, 0]
        ])
        y = np.array([[1, 1, 1, 1], [0, 0, 0, 1]])

        assert 0.0 == ECVCOp.threshold_cal(y, matrix=matrix, method="default")
        assert 0.575 == ECVCOp.threshold_cal(y, matrix=matrix, method="mean")


class TestECVC:
    def test_window_size(self):
        ecvc = ECVCDetector(config=ECVCDetectorConfig(window_size=10))
        assert ecvc.get_window_size() == 10

        ecvc = ECVCDetector(config=ECVCDetectorConfig(window_size=7))
        assert ecvc.get_window_size() == 7

    def test_ecvc(self):
        config = {
            "detectors": {
                "ECVCDetector": {
                    "method_type": "ecvc_detector",
                    "window_size": 3,
                    "seed": 0,
                    "validation_per": 0.,
                    "threshold_method": "mean",
                    "data_use_training": 30,
                }
            }
        }

        ecvc = ECVCDetector(config=config)

        input_ = []
        for _ in range(10):
            input_.extend([schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]])

        for in_ in input_:
            ecvc.process(in_)
        assert ecvc.get_state() == "Default"

        for in_ in input_[5:15]:
            alert = ecvc.process(in_)
        assert alert is None

        for in_ in [schemas.ParserSchema({"eventID": i}) for i in [4, 4, 4, 4, 4, 4, 1, 0, 1, 1]]:
            alert = ecvc.process(in_)
        assert alert is not None

    def test_legacy_method_type_still_loads(self):
        config = {"detectors": {"ECVCDetector": {"method_type": "ecvc_detector_detector", "window_size": 3}}}

        with pytest.warns(DeprecationWarning, match="ecvc_detector_detector"):
            ecvc = ECVCDetector(config=config)

        assert ecvc.config.method_type == "ecvc_detector"
        assert ecvc.config.window_size == 3
        assert "ecvc_detector_detector" in str(config)  # caller's dict is left untouched

    def test_window_seen_in_training_skips_the_scan(self, monkeypatch):
        ecvc = ECVCDetector(config=ECVCDetectorConfig(window_size=3, validation_per=0.))
        ecvc.train(_window([0, 1, 4]))
        ecvc.post_train()
        scored = []
        monkeypatch.setattr(ECVCOp, "calculate_score", staticmethod(lambda y, matrix: scored.append(y) or 1.))

        assert not ecvc.detect(_window([4, 0, 1]), schemas.DetectorSchema())  # same counts
        assert scored == []
        assert ecvc.detect(_window([4, 4, 4]), schemas.DetectorSchema())
        assert len(scored) == 1

    def test_detect_matches_the_full_scan(self):
        """The shortcut changes no decision: not for validation vectors, not for eventID -1."""
        rng = np.random.default_rng(0)
        windows = [_window(rng.integers(-1, 6, 4).tolist()) for _ in range(300)]
        ecvc = ECVCDetector(config=ECVCDetectorConfig(window_size=4, validation_per=0.5))
        for window in windows[:150]:
            ecvc.train(window)
        ecvc.post_train()
        assert ecvc.count_vecs is not None

        for window in windows:
            y = ECVCOp.build_one_vec(window, ecvc.count_vecs.shape[1])
            expected = _row_loop_score(y, ecvc.count_vecs) > ecvc.threshold
            assert ecvc.detect(window, schemas.DetectorSchema()) == expected


def _row_loop_score(y, matrix):
    """calculate_score before vectorising: one row of matrix at a time."""
    pad = np.zeros((matrix.shape[0], y.shape[0] - matrix.shape[1]))
    matrix_ = np.concat([matrix, pad], axis=1)

    score = np.inf
    for m in matrix_:
        dif = np.sum(np.abs(m - y))
        div = np.sum(np.max(np.concat([m[np.newaxis], y[np.newaxis]]).T, axis=1))
        score = score if score < (s := (dif / div)) else s

    return float(score)


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
        "ECVCDetector": {
            "method_type": "ecvc_detector",
            "window_size": 10,
            "seed": 0,
            "validation_per": 0.,
            "threshold_method": "mean",
            "data_use_training": TRAIN_UNTIL,
        },
        "ECVCDetector_fed": {
            "method_type": "ecvc_detector_detector",
            "window_size": 10,
            "allow_fed": True,
            "seed": 0,
            "validation_per": 0.,
            "threshold_method": "mean",
            "data_use_training": TRAIN_UNTIL,
        }
    }
}


class TestECVCDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.ignored
    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector = ECVCDetector(config=PIPELINE_CONFIG)

        detected_ids = set()
        for parsed_log in From.log(parser, in_path=AUDIT_LOG, do_process=True):
            alert = detector.process(parsed_log)
            if detector.get_state() == "Default" and alert is not None:
                detected_ids.update(set([log_id for log_id in alert["logIDs"]]))

        for log_id in {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}:
            assert log_id in detected_ids

    @pytest.mark.ignored
    def test_audit_log_anomalies_to_binary(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector1 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)
        detector2 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs:
            detector1.process(log)

        thress = detector1.threshold
        binary = detector1.to_binary()
        detector2 = detector2.from_binary(binary)

        assert detector2.persistency == detector1.persistency
        assert (detector2.count_vecs == detector1.count_vecs).all()
        assert detector2.threshold == thress

    @pytest.mark.ignored
    def test_audit_log_anomalie_fed(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector1 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)
        detector2 = ECVCDetector(name="ECVCDetector_fed", config=PIPELINE_CONFIG)

        logs = list(From.log(parser, in_path=AUDIT_LOG, do_process=True))
        for log in logs:
            detector1.process(log)

        thress = detector1.threshold
        (detector1 + detector2).aggregate()

        assert detector2.persistency == detector1.persistency
        assert (detector2.count_vecs == detector1.count_vecs).all()
        assert detector2.threshold == thress


def _window(event_ids):
    return [schemas.ParserSchema({"eventID": i}) for i in event_ids]


def _fed_detector(window_size):
    return ECVCDetector(config=ECVCDetectorConfig(window_size=window_size, allow_fed=True))


class TestECVCDetectorRestoredState:
    """State that arrives after construction warns on a window-size mismatch
    and rebuilds the count vectors."""

    def test_from_binary_warns_and_rebuilds_count_vectors(self, tmp_path, monkeypatch, caplog):
        monkeypatch.chdir(tmp_path)  # the slow store writes .temp/ CSVs here
        trained = _fed_detector(3)
        trained.train(_window([0, 1, 4]))

        with caplog.at_level(logging.WARNING):
            restored = _fed_detector(4).from_binary(trained.to_binary())

        assert any("window_size 3" in r.message for r in caplog.records)
        assert restored.count_vecs is not None

    def test_aggregate_warns_and_rebuilds_count_vectors(self, tmp_path, monkeypatch, caplog):
        monkeypatch.chdir(tmp_path)
        trained = _fed_detector(3)
        trained.train(_window([0, 1, 4]))
        receiver = _fed_detector(4)

        with caplog.at_level(logging.WARNING):
            (receiver + trained).aggregate()

        assert any("window_size 3" in r.message for r in caplog.records)
        assert receiver.count_vecs is not None

    def test_finalize_federation_removes_the_slow_table(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        detector = _fed_detector(3)
        detector.train(_window([0, 1, 4]))
        assert (tmp_path / ".temp").exists()

        detector.finalize_federation()

        assert not (tmp_path / ".temp").exists()
