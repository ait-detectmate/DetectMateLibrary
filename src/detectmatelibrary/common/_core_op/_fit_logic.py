
from enum import Enum


class TrainState(Enum):
    DEFAULT = 0
    STOP_TRAINING = 1
    KEEP_TRAINING = 2

    def describe(self) -> str:
        descriptions = [
            "Follow default training behavior.",
            "Force stop training.",
            "Keep training regardless of default behavior."
        ]

        return descriptions[self.value]


class ConfigState(Enum):
    DEFAULT = 0
    STOP_CONFIGURE = 1
    KEEP_CONFIGURE = 2

    def describe(self) -> str:
        descriptions = [
            "Follow default configuration behavior.",
            "Force stop configuration.",
            "Keep configuring regardless of default behavior."
        ]

        return descriptions[self.value]


def do_training(
    data_use_training: int | None, index: int, train_state: TrainState
) -> bool:
    if train_state == TrainState.STOP_TRAINING:
        return False
    elif train_state == TrainState.KEEP_TRAINING:
        return True

    return data_use_training is not None and data_use_training > index


def do_configure(
    data_use_configure: int | None, index: int, configure_state: ConfigState
) -> bool:
    if configure_state == ConfigState.STOP_CONFIGURE:
        return False
    elif configure_state == ConfigState.KEEP_CONFIGURE:
        return True

    return data_use_configure is not None and data_use_configure > index


class FitLogicState(Enum):
    DO_CONFIG = 0
    DO_TRAIN = 1
    NOTHING = 2


class FitLogic:
    def __init__(
        self, data_use_configure: int | None, data_use_training: int | None
    ) -> None:
        
        self.train_state = TrainState.DEFAULT
        self.configure_state = ConfigState.DEFAULT

        self.data_used_train = 0
        self.data_used_configure = 0

        self._configuration_done = False
        self.config_finished = False

        self._training_done = False
        self.training_finished = False

        self.data_use_configure = data_use_configure
        self.data_use_training = data_use_training

    def finish_config(self) -> bool:
        if self._configuration_done and not self.config_finished:
            self.config_finished = True
            return True

        return False

    def finish_training(self) -> bool:
        if self._training_done and not self.training_finished:
            self.training_finished = True
            return True

        return False

    def run(self) -> FitLogicState:
        if do_configure(
            data_use_configure=self.data_use_configure,
            index=self.data_used_configure,
            configure_state=self.configure_state
        ):
            self.data_used_configure += 1
            return FitLogicState.DO_CONFIG
        else:
            if self.data_used_configure > 0 and not self._configuration_done:
                self._configuration_done = True

            if do_training(
                data_use_training=self.data_use_training,
                index=self.data_used_train,
                train_state=self.train_state
            ):
                self.data_used_train += 1
                return FitLogicState.DO_TRAIN
            elif self.data_used_train > 0 and not self._training_done:
                self._training_done = True

        return FitLogicState.NOTHING