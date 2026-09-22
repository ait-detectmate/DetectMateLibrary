from typing import Self, Any

import polars as pl
import csv
import os


class Manager:
    def __init__(self, path: str) -> None:
        self.test_buffer: list[Any] = []

    def add_rows(self, rows: list[Any]) -> None:
        self.test_buffer.extend(rows)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args, **kwargs) -> None:  # type: ignore
        self.close()


class CsvManager(Manager):
    def __init__(self, path: str) -> None:
        self.file = open(
            path,
            mode="a",
            newline="",
            encoding="utf-8",
        )
        self.writer = csv.writer(self.file)

    def add_rows(self, rows: list[Any]) -> None:
        self.writer.writerows(rows)

    def flush(self) -> None:
        self.file.flush()

    def close(self) -> None:
        self.file.close()


class Table:
    def __init__(self, path: str) -> None:
        self.path = path

    def file2DataFrame(self) -> pl.DataFrame:
        return pl.read_csv(self.path)


class SlowPersistency:
    def __init__(
        self,
        columns: list[str],
        path: str = ".slow_persistency.csv",
        file_manager: type[CsvManager] = CsvManager,
        buffer_size: int = 10
    ) -> None:

        self.path = path
        self.buffer_max_size = buffer_size
        self.buffer_current_size = 0
        self.buffer: list[list[Any]] = []

        self.reset()
        self.file_manager = file_manager(path=path)
        self.table = Table(self.path)
        self._insertion([columns])

    def _insertion(self, rows: list[list[str]]) -> None:
        self.file_manager.add_rows(rows)
        self.file_manager.flush()

    def push_buffer(self) -> None:
        self.buffer_current_size = 0
        self._insertion(self.buffer)
        self.buffer = []

    def reset(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)

    def add(self, row: list[Any]) -> None:
        self.buffer.append(row)
        self.buffer_current_size += 1

        if self.buffer_current_size >= self.buffer_max_size:
            self.push_buffer()

    def close(self) -> None:
        self.file_manager.close()
