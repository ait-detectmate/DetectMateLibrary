from abc import abstractmethod
from typing import Any, Callable, Literal, Optional
from components.Base.ComponentBase import ConfigBase
from components.utils.DataBuffer import DataBuffer
from components.Base.ComponentBase import ComponentBase


class ParserBase(ComponentBase):
    def __init__(
        self,
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[ConfigBase | dict] = None
    ):
        self.process_function: Callable[[Any, ConfigBase], Any] = self.parse
        self.data_buffer = DataBuffer(
            mode=buffer_mode,
            size=buffer_size,
            process_function=self.process_function,
        )
        if isinstance(config, dict):
            self.config = ConfigBase(**config)
        elif isinstance(config, ConfigBase):
            self.config = config
        else:
            self.config = ConfigBase()

    @abstractmethod
    def parse(self, data: Any, config: ConfigBase):
        pass

    @abstractmethod
    def train(self, data: Any, config: ConfigBase) -> None:
        pass

    def _process(self, data: Any, config: ConfigBase):
        # schema validation?
        if config:
            self.config.update_config(config.get_config())
        return self.data_buffer.add(data)
