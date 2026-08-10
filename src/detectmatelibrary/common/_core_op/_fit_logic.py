
from typing import Literal, get_args
from enum import Enum
import warnings

# Individual state of config or train ################################################

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

    def force_keep_doing(self) -> None:
        self.current = EnumState.KEEP

    def keep_doing(self) -> bool:
        if self.current == EnumState.STOP:
            return False
        if self.current == EnumState.KEEP:
            return True

        return self.total_need_data is not None and self.total_need_data > self.data_used

    def force_finish(self) -> None:
        self.current = EnumState.STOP
        self.finished, self.ready_to_finish = False, True

    def check_if_ready_finish(self) -> None:
        if self.data_used > 0 and not self.ready_to_finish:
                self.ready_to_finish = True

    def is_finish(self) -> bool:
        if self.ready_to_finish and not self.finished:
            self.finished = True
            return True
        return False


# Overall state of the core component ##################################################

StatesL = Literal["keep_training", "stop_training", "keep_configuring", "stop_configuring"]


class FitLogicState(Enum):
    DO_CONFIG = 0
    DO_TRAIN = 1
    NOTHING = 2

    def describe(self) -> str:
        descriptions = [
            "Configuring",
            "Training",
            "Default"
        ]
        return descriptions[self.value]


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
        if state == "keep_training":
            self.train_state.force_keep_doing()
        elif state == "stop_training":
            self.train_state.force_finish()
        elif state == "keep_configuring":
            self.config_state.force_keep_doing()
        elif state == "stop_configuring":
            self.config_state.force_finish()
        else:
            warnings.warn(f"State {state} unknown, use: {get_args(StatesL)}")

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