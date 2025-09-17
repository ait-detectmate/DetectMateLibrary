from src.components.common.core import CoreComponent, ConfigCore
from src.components.utils.data_buffer import ArgsBuffer
import src.schemas as schemas

from typing import Any, Literal, Optional


class CoreParser(CoreComponent):
    def __init__(
        self,
        name: str = "CoreParser",
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
            process_function=self.parse,
            args_buffer=ArgsBuffer(
                mode=buffer_mode, size=buffer_size
            ),
            input_schema=schemas.LOG_SCHEMA,
            output_schema=schemas.PARSER_SCHEMA,
        )

    def parse(self, data: Any, config: ConfigCore):
        pass

    def train(self, data: Any, config: ConfigCore) -> None:
        pass
