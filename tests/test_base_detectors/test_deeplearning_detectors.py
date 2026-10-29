
from detectmatelibrary.base_detectors import (
    DeepLearningDetector, DeepLearningDetectorConfig
)

from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary import schemas

from pydantic import ValidationError
import pytest
import yaml


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


class RecordingDeepModel(DeepModel):
    """Remembers the window lists the detector hands to finetune and train."""

    def __init__(self, *args, **kargs):
        super().__init__()
        self.finetune_seqs = None
        self.train_seqs = None

    def check_anomaly(self, seq, top_k):
        return False

    def train(self, seqs, var_per):
        self.train_seqs = seqs
        return {}

    def finetune(self, seqs, var_per, epochs=2):
        self.finetune_seqs = seqs


def _fed_detector(n: int, **config) -> DeepLearningDetector:
    """A detector holding the windows (i,) for i < n in both lists."""
    detector = DeepLearningDetector(
        model_cls=RecordingDeepModel, config=DeepLearningDetectorConfig(window_size=1, **config)
    )
    for i in range(n):
        detector.configure([schemas.ParserSchema({"eventID": i})])
        detector.train([schemas.ParserSchema({"eventID": i})])
    return detector


def _kept(n: int, **config) -> tuple[list, list]:
    """The (finetune, train) window lists the model receives."""
    detector = _fed_detector(n, **config)
    detector.set_configuration()
    detector.post_train()
    return detector.model.finetune_seqs, detector.model.train_seqs


class TestTrainSample:
    def test_default_passes_lists_through(self):
        detector = _fed_detector(50)
        config_seqs, train_seqs = detector.config_seqs, detector.train_seqs
        assert detector.config.train_sample == 1.0

        detector.set_configuration()
        detector.post_train()

        assert detector.model.finetune_seqs is config_seqs
        assert detector.model.train_seqs is train_seqs
        assert train_seqs == [(i,) for i in range(50)]

    @pytest.mark.parametrize("n, expected", [(1000, 100), (25, 2), (9, 1), (1, 1)])
    def test_keeps_share_rounded_down_at_least_one(self, n, expected):
        finetune_seqs, train_seqs = _kept(n, train_sample=0.1)
        assert len(finetune_seqs) == expected
        assert len(train_seqs) == expected

    def test_empty_lists_stay_empty(self):
        assert _kept(0, train_sample=0.1) == ([], [])

    def test_kept_windows_stay_in_log_order(self):
        for seqs in _kept(1000, train_sample=0.1):
            assert seqs == sorted(seqs)
            assert len(set(seqs)) == len(seqs)
            assert set(seqs) <= {(i,) for i in range(1000)}

    def test_same_seed_same_windows(self):
        first = _kept(1000, train_sample=0.1, train_sample_seed=3)
        assert first == _kept(1000, train_sample=0.1, train_sample_seed=3)

    def test_different_seed_different_windows(self):
        _, seed_0 = _kept(1000, train_sample=0.1, train_sample_seed=0)
        _, seed_1 = _kept(1000, train_sample=0.1, train_sample_seed=1)
        assert seed_0 != seed_1

    def test_sample_is_spread_over_the_log(self):
        _, train_seqs = _kept(1000, train_sample=0.1)
        assert train_seqs[0][0] < 100 and train_seqs[-1][0] > 900

    @pytest.mark.parametrize("share", [0.0, -0.1, 1.01])
    def test_share_outside_zero_one_is_rejected(self, share):
        with pytest.raises(ValidationError):
            DeepLearningDetectorConfig(train_sample=share)

    def test_round_trips_through_yaml(self):
        config = yaml.safe_load(
            """
            detectors:
              MyDL:
                method_type: core_detector
                auto_config: false
                params:
                  window_size: 5
                  train_sample: 0.1
                  train_sample_seed: 7
            """
        )
        loaded = DeepLearningDetectorConfig.from_dict(config, "MyDL")
        assert loaded.train_sample == 0.1
        assert loaded.train_sample_seed == 7

        dumped = loaded.to_dict("MyDL")
        params = dumped["detectors"]["MyDL"]["params"]
        assert params["train_sample"] == 0.1
        assert params["train_sample_seed"] == 7
        reloaded = DeepLearningDetectorConfig.from_dict(yaml.safe_load(yaml.safe_dump(dumped)), "MyDL")
        assert (reloaded.train_sample, reloaded.train_sample_seed) == (0.1, 7)
