from src.components.common.core import CoreComponent, ConfigCore
from src.components.utils.DataBuffer import ArgsBuffer
import src.schemas as schemas

from typing import Any, Literal, Optional


class CoreDetector(CoreComponent):
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
            type_="Detector",
            config=config,
            args_buffer=ArgsBuffer(
                mode=buffer_mode, size=buffer_size, process_function=self.detect
            ),
            input_schema=schemas.PARSER_SCHEMA,
            output_schema=schemas.DETECTOR_SCHEMA,
        )

    def detect(self, data: Any, config: ConfigCore):
        pass

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
