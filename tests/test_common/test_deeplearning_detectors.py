
from detectmatelibrary.common.deeplearning_detector import (
    DeepLearningDetector, DeepLearningDetectorConfig
)

from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary import schemas

import pytest


class Flag(Exception):
    pass


class DummyDeepModel(DeepModel):
    def __init__(self, *args, **kargs):
        super().__init__()

    def check_anomaly(self, seq, top_k):
        raise Flag()

    def train(self, seqs, var_per):
        return {}

    def finetune(self, seqs, var_per, epochs):
        return None


class TestDeepLearning:
    def test_normal_run_configure(self):
        deep_learning_detector = DeepLearningDetector(
            model_cls=DummyDeepModel, config=DeepLearningDetectorConfig(window_size=1)
        )

        for i in range(10):
            deep_learning_detector.configure(
                [schemas.ParserSchema({"EventID": i})]
            )

        for i in range(10):
            assert deep_learning_detector.config_seqs[i] == (i,)

        deep_learning_detector.set_configuration()
        assert len(deep_learning_detector.config_seqs) == 0

    def test_normal_run_train(self):
        deep_learning_detector = DeepLearningDetector(
            model_cls=DummyDeepModel, config=DeepLearningDetectorConfig(window_size=1)
        )

        for i in range(10):
            deep_learning_detector.train(
                [schemas.ParserSchema({"EventID": i})]
            )

        for i in range(10):
            assert deep_learning_detector.train_seqs[i] == (i,)

        deep_learning_detector.post_train()
        assert len(deep_learning_detector.train_seqs) == 0

    def test_check_that_check_anomaly_is_call(self):
        deep_learning_detector = DeepLearningDetector(
            model_cls=DummyDeepModel, config=DeepLearningDetectorConfig(window_size=1)
        )

        with pytest.raises(Flag):
            deep_learning_detector.process(schemas.ParserSchema({"EventID": 0}))
