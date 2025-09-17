from components.utils.DataBuffer import DataBuffer
from components.common.core import CoreComponent, ConfigCore


from typing import Any, Literal, Optional
from abc import abstractmethod


class DetectorBase(CoreComponent):
    def __init__(
        self,
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[ConfigCore | dict] = None
    ):
        self.data_buffer = DataBuffer(
            mode=buffer_mode,
            size=buffer_size,
            process_function=self.detect,
        )
        if isinstance(config, dict):
            self.config = ConfigCore(**config)
        elif isinstance(config, ConfigCore):
            self.config = config
        else:
            self.config = ConfigCore()

    @abstractmethod
    def detect(self, data: Any, config: ConfigCore):
        pass

    @abstractmethod
    def train(self, data: Any, config: ConfigCore) -> None:
        pass

    def process(self, data, learnmode=False, config=None):
        # schema validation?
        if config:
            self.config.update_config(config.get_config())
        if learnmode:
            return self.train(data, self.config)
        else:
            return self.detect(data, self.config)
