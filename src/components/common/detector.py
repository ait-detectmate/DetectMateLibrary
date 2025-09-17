from abc import ABC, abstractmethod
from src.components.common.core import CoreComponent, ConfigCore
from src.components.utils.data_buffer import ArgsBuffer
import src.schemas as schemas

from typing import Any, Literal, Optional


class CoreDetector(CoreComponent, ABC):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[ConfigCore | dict] = ConfigCore()
    ):
        if isinstance(config, dict):
            config = ConfigCore.from_dict(config)

        super().__init__(
            name=name,
            type_="Parser",
            config=config,
            train_function=self.train,
            process_function=self.detect,
            args_buffer=ArgsBuffer(
                mode=buffer_mode, size=buffer_size
            ),
            input_schema=schemas.PARSER_SCHEMA,
            output_schema=schemas.DETECTOR_SCHEMA,
        )

    @abstractmethod
    def detect(self, data: Any) -> Any: return data

    @abstractmethod
    def train(self, data: Any) -> None: ...
