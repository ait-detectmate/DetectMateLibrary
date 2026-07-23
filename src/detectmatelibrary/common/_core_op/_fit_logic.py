
from typing import Literal, get_args
from enum import Enum
import warnings


class FitLogicState(Enum):
    DO_CONFIG = 0
    DO_TRAIN = 1
    NOTHING = 2

    def describe(self) -> str:
        descriptions = [
            "Configuring",
            "Training.",
            "Default"
        ]
        return descriptions[self.value]


class EnumState(Enum):
    DEFAULT = 0
    STOP = 1
    KEEP = 2

    def describe(self) -> str:
        descriptions = [
            "Follow default behavior.",
            "Force stop",
            "Keep doing it regardless of default behavior."
        ]
        return descriptions[self.value]


class State:
    def __init__(self, total_need_data: int | None) -> None:
        self.total_need_data = total_need_data

        self.ready_to_finish = False
        self.finished = False
        self.data_used = 0
        self.current = EnumState.DEFAULT

    def keep_doing(self) -> bool:
        if self.current == EnumState.STOP:
            return False
        if self.current == EnumState.KEEP:
            return True

        return self.total_need_data is not None and self.total_need_data > self.data_used

    def force_finish(self) -> None:
        self.finished, self.ready_to_finish = False, True

    def check_if_ready_finish(self) -> None:
        if self.data_used > 0 and not self.ready_to_finish:
                self.ready_to_finish = True

    def is_finish(self) -> bool:
        if self.ready_to_finish and not self.finished:
            self.finished = True
            return True
        return False


StatesL = Literal["keep_training", "stop_training", "keep_configuring", "stop_configuring"]


def update_state(
    state: StatesL, train_state: EnumState, config_state: EnumState
) -> tuple[EnumState, EnumState]:
    if state == "keep_training":
        train_state = EnumState.KEEP
    elif state == "stop_training":
        train_state = EnumState.STOP
    elif state == "keep_configuring":
        config_state = EnumState.KEEP
    elif state == "stop_configuring":
        config_state = EnumState.STOP
    else:
        warnings.warn(f"State {state} unknown, use: {get_args(StatesL)}")

    return train_state, config_state


class FitLogic:
    def __init__(
        self, data_use_configure: int | None, data_use_training: int | None
    ) -> None:
        
        self.last_state = FitLogicState.NOTHING

        self.config_state = State(data_use_configure)
        self.train_state = State(data_use_training)

    def get_last_state(self) -> str:
        return self.last_state.describe()

    def update_state(self, state: StatesL) -> None:
        self.train_state.current, self.config_state.current = update_state(
            state=state, train_state=self.train_state.current, config_state=self.config_state.current
        )
        if self.config_state.current == EnumState.STOP:
            self.config_state.force_finish()
            
        if self.train_state.current == EnumState.STOP:
            self.train_state.force_finish()

    def finish_config(self) -> bool:
        return self.config_state.is_finish()

    def finish_training(self) -> bool:
        return self.train_state.is_finish()

    def __check_state(self) -> FitLogicState:
        if self.config_state.keep_doing():
            self.config_state.data_used += 1
            return FitLogicState.DO_CONFIG
        else:
            self.config_state.check_if_ready_finish()

            if self.train_state.keep_doing():
                self.train_state.data_used += 1
                return FitLogicState.DO_TRAIN
            self.train_state.check_if_ready_finish()

        return FitLogicState.NOTHING
    
    def run(self) -> FitLogicState:
        self.last_state = self.__check_state()
        return self.last_state