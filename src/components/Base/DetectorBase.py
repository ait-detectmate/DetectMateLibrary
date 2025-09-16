from abc import abstractmethod
from typing import Any, Literal, Optional
from components.Base.ConfigBase import ConfigBase
from components.utils.DataBuffer import DataBuffer
from components.Base.ComponentBase import ComponentBase


class DetectorBase(ComponentBase):
    def __init__(
        self,
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[ConfigBase | dict] = None
    ):
        self.data_buffer = DataBuffer(
            mode=buffer_mode,
            size=buffer_size,
            process_function=self.detect,
        )
        if isinstance(config, dict):
            self.config = ConfigBase(**config)
        elif isinstance(config, ConfigBase):
            self.config = config
        else:
            self.config = ConfigBase()

    @abstractmethod
    def detect(self, data: Any, config: ConfigBase):
        pass

    @abstractmethod
    def train(self, data: Any, config: ConfigBase) -> None:
        pass

    def process(self, data, learnmode=False, config=None):
        # schema validation?
        if config:
            self.config.update_config(config.get_config())
        if learnmode:
            return self.train(data, self.config)
        else:
            return self.detect(data, self.config)
