"""Tests for FitLogic training lifecycle hooks."""

from detectmatelibrary.common._core_op._fit_logic import (
    FitLogic, FitLogicState, TrainState
)


class TestFinishTraining:
    """Test that finish_training() fires exactly once after bounded training."""

    def test_finish_training_fires_once_after_bounded_training(self) -> None:
        logic = FitLogic(data_use_configure=None, data_use_training=3)
        finish_calls = []
        for _ in range(6):
            logic.run()
            finish_calls.append(logic.finish_training())
        assert finish_calls.count(True) == 1

    def test_finish_training_fires_on_first_nothing_after_training(self) -> None:
        logic = FitLogic(data_use_configure=None, data_use_training=2)
        states = []
        finishes = []
        for _ in range(5):
            state = logic.run()
            states.append(state)
            finishes.append(logic.finish_training())
        # First two calls are DO_TRAIN, third is first NOTHING
        assert states[:2] == [FitLogicState.DO_TRAIN, FitLogicState.DO_TRAIN]
        assert states[2] == FitLogicState.NOTHING
        assert finishes[2] is True
        assert all(not f for f in finishes[:2])
        assert all(not f for f in finishes[3:])

    def test_finish_training_not_called_without_training(self) -> None:
        logic = FitLogic(data_use_configure=None, data_use_training=None)
        for _ in range(5):
            logic.run()
            assert logic.finish_training() is False

    def test_finish_training_not_called_during_training(self) -> None:
        logic = FitLogic(data_use_configure=None, data_use_training=5)
        for _ in range(5):
            state = logic.run()
            assert state == FitLogicState.DO_TRAIN
            assert logic.finish_training() is False

    def test_finish_training_not_called_with_keep_training(self) -> None:
        logic = FitLogic(data_use_configure=None, data_use_training=None)
        logic.train_state = TrainState.KEEP_TRAINING
        for _ in range(10):
            state = logic.run()
            assert state == FitLogicState.DO_TRAIN
            assert logic.finish_training() is False

    def test_finish_training_after_configure_and_training(self) -> None:
        """finish_training fires correctly even when configure phase precedes training."""
        logic = FitLogic(data_use_configure=2, data_use_training=3)
        finish_calls = []
        for _ in range(8):
            logic.run()
            finish_calls.append(logic.finish_training())
        assert finish_calls.count(True) == 1
