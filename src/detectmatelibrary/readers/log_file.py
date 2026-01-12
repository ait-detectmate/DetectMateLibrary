from detectmatelibrary.common.reader import CoreReaderConfig, CoreReader

from detectmatelibrary import schemas

from typing import Optional, Iterator
import os


class LogsNotFoundError(Exception):
    pass


class LogsNoPermissionError(Exception):
    pass


class LogFileConfig(CoreReaderConfig):
    file: str = "<PLACEHOLDER>"
    method_type: str = "log_file_reader"


class LogFileReader(CoreReader):
    def __init__(
        self,
        name: str = "File_reader",
        config: Optional[LogFileConfig | dict] = LogFileConfig(),
    ) -> None:
        
        if isinstance(config, dict):
            config = LogFileConfig.from_dict(config, name)
        
        super().__init__(name=name, config=config)
        self.__log_generator = self.read_logs()
        self.is_over = False

    def read_logs(self) -> Iterator[str]:
        path = self.config.file
        if not os.path.exists(path):
            raise LogsNotFoundError(f"Logs file not found at: {path}")
        if not os.access(path, os.R_OK):
            raise LogsNoPermissionError(
                f"You do not have the permission to access logs: {path}"
            )

        with open(path, "r") as file:
            for line in file:
                yield line.strip()  
        yield None  

    def read(self, output_: schemas.LogSchema) -> bool:
        if not self.is_over:
            log = next(self.__log_generator)

            if log is None:
                self.is_over = True
            else:
                output_.log = log

        return not self.is_over

    def reset(self) -> None:
        self.__log_generator = self.read_logs()
        self.is_over = False