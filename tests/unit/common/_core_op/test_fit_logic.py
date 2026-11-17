"""Tests for FitLogic training lifecycle hooks."""
import pytest

from detectmatelibrary.common._core_op._fit_logic import (
    FitLogic, FitLogicState, EnumState
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
        logic.train_state.current = EnumState.KEEP
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

    def test_force_stop_config(self) -> None:
        logic = FitLogic(data_use_configure=20, data_use_training=None)

        # Stop in the middle
        assert not logic.finish_config()
        logic.update_state("stop_configuring")
        assert logic.finish_config()
        assert not logic.finish_config()

        # Stop after a force start 
        logic.update_state("keep_configuring")
        assert not logic.finish_config()
        logic.update_state("stop_configuring")
        assert logic.finish_config()

    def test_force_stop_train(self) -> None:
        logic = FitLogic(data_use_configure=None, data_use_training=20)

        # Stop in the middle
        assert not logic.finish_training()
        logic.update_state("stop_training")
        assert logic.finish_training()
        assert not logic.finish_training()

        # Stop after a force start 
        logic.update_state("keep_training")
        assert not logic.finish_training()
        logic.update_state("stop_training")
        assert logic.finish_training()


CONFIGURING, TRAINING, DETECTING = FitLogicState.DO_CONFIG, FitLogicState.DO_TRAIN, FitLogicState.NOTHING


@pytest.mark.parametrize("commands, expected", [
    # with no data_use_* settings a component only detects, until told otherwise
    ([None], [DETECTING]),
    (["keep_configuring", "stop_configuring"], [CONFIGURING, DETECTING]),
    (["keep_training", "stop_training"], [TRAINING, DETECTING]),
    # the configure phase wins: training commands wait until it is stopped
    (["keep_configuring", "stop_training", "keep_training"], [CONFIGURING, CONFIGURING, CONFIGURING]),
    (["keep_configuring", "keep_training", "stop_configuring"], [CONFIGURING, CONFIGURING, TRAINING]),
    # a stopped configure phase can be started again
    (["keep_configuring", "stop_configuring", "keep_configuring"], [CONFIGURING, DETECTING, CONFIGURING]),
], ids=["no_phases", "configure", "train", "configure_first", "train_after_configure", "configure_again"])
def test_state_commands(commands, expected):
    """update_state() commands, one per record: the phase each record ends up in."""
    logic = FitLogic(data_use_configure=None, data_use_training=None)
    states = []
    for command in commands:
        if command is not None:
            logic.update_state(command)
        states.append(logic.run())
    assert states == expected
