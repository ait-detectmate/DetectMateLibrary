from components.common.core import CoreComponent, ConfigCore
from components.utils.DataBuffer import DataBuffer

from typing import Any, Callable, Literal, Optional
from abc import abstractmethod


class ParserBase(CoreComponent):
    def __init__(
        self,
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[ConfigCore | dict] = None
    ):
        self.process_function: Callable[[Any, ConfigCore], Any] = self.parse
        self.data_buffer = DataBuffer(
            mode=buffer_mode,
            size=buffer_size,
            process_function=self.process_function,
        )
        if isinstance(config, dict):
            self.config = ConfigCore(**config)
        elif isinstance(config, ConfigCore):
            self.config = config
        else:
            self.config = ConfigCore()

    @abstractmethod
    def parse(self, data: Any, config: ConfigCore):
        pass

    @abstractmethod
    def train(self, data: Any, config: ConfigCore) -> None:
        pass

    def _process(self, data: Any, config: ConfigCore):
        # schema validation?
        if config:
            self.config.update_config(config.get_config())
        return self.data_buffer.add(data)
