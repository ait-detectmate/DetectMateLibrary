
from detectmatelibrary.base_detectors import (
    DeepLearningDetector, DeepLearningDetectorConfig
)
from detectmatelibrary.base_detectors.deeplearning_detector import SessionWindows
from detectmatelibrary.utils.deep_learning._op import PAD

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

    def finetune(self, seqs, var_per, epochs=2):
        return None


class TestDeepLearning:
    def test_normal_run_configure(self):
        deep_learning_detector = DeepLearningDetector(
            model_cls=DummyDeepModel, config=DeepLearningDetectorConfig(window_size=1)
        )

        for i in range(10):
            deep_learning_detector.configure(
                [schemas.ParserSchema({"eventID": i})]
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
                [schemas.ParserSchema({"eventID": i})]
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
            deep_learning_detector.process(schemas.ParserSchema({"eventID": 0}))


class RecordingModel(DeepModel):
    def __init__(self, *args, **kargs):
        super().__init__()
        self.checked, self.trained, self.configured = [], [], []

    def check_anomaly(self, seq, top_k):
        self.checked.append(seq)
        return False

    def train(self, seqs, var_per):
        self.trained = list(seqs)
        return {}

    def finetune(self, seqs, var_per, epochs=2):
        self.configured = list(seqs)


def record(event, session):
    return schemas.ParserSchema({"eventID": event, "headerVariables": {"blk": session}})


# Two interleaved sessions, a: 1 3 5 and b: 2 4, and the window (size 3) ending at each event.
STREAM = [("a", 1), ("b", 2), ("a", 3), ("b", 4), ("a", 5)]
WINDOWS = [(PAD, PAD, 1), (PAD, PAD, 2), (PAD, 1, 3), (PAD, 2, 4), (1, 3, 5)]


class TestSessionWindows:
    def test_windows_never_mix_sessions(self):
        windows = SessionWindows(size=3)
        assert [windows.add(s, e) for s, e in STREAM] == WINDOWS

    def test_every_event_is_checked_in_its_own_session(self):
        detector = DeepLearningDetector(
            model_cls=RecordingModel,
            config=DeepLearningDetectorConfig(window_size=3, session_variable="blk"),
        )
        for s, e in STREAM:
            detector.process(record(e, s))
        assert detector.model.checked == WINDOWS

    def test_each_phase_sees_each_event_once(self):
        # Configure records are replayed into train() after the configure phase, and only
        # the records after it reach detect(): the windows must not count an event twice
        # or lose one.
        detector = DeepLearningDetector(
            model_cls=RecordingModel,
            config=DeepLearningDetectorConfig(
                window_size=3, session_variable="blk", data_use_configure=2, data_use_training=1
            ),
        )
        for s, e in STREAM:
            detector.process(record(e, s))
        assert detector.model.configured == WINDOWS[:2]
        assert detector.model.trained == WINDOWS[:3]
        assert detector.model.checked == WINDOWS[2:]

    def test_missing_session_variable_raises(self):
        detector = DeepLearningDetector(
            model_cls=RecordingModel,
            config=DeepLearningDetectorConfig(window_size=3, session_variable="blk"),
        )
        with pytest.raises(ValueError, match="blk"):
            detector.process(schemas.ParserSchema({"eventID": 1}))
