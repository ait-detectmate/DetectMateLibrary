
from detectmatelibrary.detectors.ecvc_detector import ECVCOp, ECVCDetectorConfig, ECVCDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from detectmatelibrary import schemas

from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

import numpy as np


class TestECVCOP:
    def test_build_count_vec(self):
        input_ = [
            schemas.ParserSchema({"EventID": i}) for i in [0, 1, 4, 0]
        ]
        expected = tuple([2, 1, 0, 0, 1])

        assert ECVCOp.build_count_vec(input_) == expected

    def test_build_one_vec(self):
        input_ = [
            schemas.ParserSchema({"EventID": i}) for i in [0, 1, 4, 0]
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
                    "method_type": "ecvc_detector_detector",
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
            input_.extend([schemas.ParserSchema({"EventID": i}) for i in [0, 1, 4, 0]])

        for in_ in input_:
            ecvc.process(in_)
        assert ecvc.get_state() == "Default"

        for in_ in input_[5:15]:
            alert = ecvc.process(in_)
        assert alert is None

        for in_ in [schemas.ParserSchema({"EventID": i}) for i in [4, 4, 4, 4, 4, 4, 1, 0, 1, 1]]:
            alert = ecvc.process(in_)
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
        "ECVCDetector": {
            "method_type": "ecvc_detector_detector",
            "window_size": 10,
            "seed": 0,
            "validation_per": 0.,
            "threshold_method": "mean",
            "data_use_training": TRAIN_UNTIL,
        }
    }
}


class TestECVCDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

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
