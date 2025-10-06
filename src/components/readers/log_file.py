
from src.components.common.reader import CoreReaderConfig, CoreReader
from src.components.utils.id_generator import SimpleIDGenerator

import src.schemas as schemas

from typing import Optional, Iterator


class LogFileConfig(CoreReaderConfig):
    file: str = "file.log"


class LogFileReader(CoreReader):
    def __init__(
        self,
        name: str="File_reader",
        config: Optional[LogFileConfig | dict] = LogFileConfig(),
        id_generator: SimpleIDGenerator = SimpleIDGenerator,
    ) -> None:
        super().__init__(
            name=name, config=config, id_generator=id_generator
        )
        self.__log_generator = self.__read_logs()
        self.is_over = False

    def __read_logs(self) -> Iterator[str]:
        with open(self.config.file, "r") as file:
            for line in file:
                yield line.strip()  
        yield None  

    def read(self, output_: schemas.SchemaT) -> bool:
        if not self.is_over:
            log = next(self.__log_generator)

            if log is None:
                self.is_over = True
            else:
                output_.log = log

        return not self.is_over