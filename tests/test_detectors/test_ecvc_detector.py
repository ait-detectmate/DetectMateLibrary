
from detectmatelibrary.detectors.ecvc_detector import ECVCOp

from detectmatelibrary import schemas

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
        assert 0.4 == ECVCOp.threshold_cal(y, matrix=matrix, method="mode")
