from abc import ABC, abstractmethod
from typing import Any, Literal, Optional
from components.Base.ConfigBase import ConfigBase
from components.utils.DataBuffer import DataBuffer


class DetectorBase(ABC):
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

    # def _process(self, data: BaseSchema, config: ConfigBase) -> BaseSchema:
    #     # schema validation?
    #     if config:
    #         self.config.update_config(config.get_config())
    #     return self.data_buffer.add(data)
