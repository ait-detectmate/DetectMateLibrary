from typing import Self, Any
import secrets
import string

from pathlib import Path
import polars as pl
import warnings
import csv
import os


def generate_path() -> str:
    if not os.path.exists(".temp"):
        os.mkdir(".temp")

    random_string = "".join(secrets.choice(string.digits) for _ in range(20))
    return f".temp/.{random_string}.csv"


def clean_generated_path() -> None:
    directory = Path(".")
    csv_files = list(directory.glob(".temp/.*.csv"))
    for file in csv_files:
        os.remove(file)

    if os.path.exists(".temp"):
        os.removedirs(".temp")


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


class SlowPersistency:
    def __init__(
        self,
        columns: list[str],
        file_manager: type[Manager] = CsvManager,
        buffer_size: int = 200
    ) -> None:

        self.path = generate_path()
        self.buffer_max_size = buffer_size
        self.buffer_current_size = 0
        self.buffer: list[list[Any]] = []
        self.cls = file_manager

        self.columns = [columns]
        self.was_created = False

    def _insertion(self, rows: list[list[str]]) -> None:
        if not self.was_created:
            self.file_manager = self.cls(path=self.path)
            self.file_manager.add_rows(self.columns)
        self.was_created = True

        self.file_manager.add_rows(rows)
        self.file_manager.flush()

    @classmethod
    def from_dataframe(cls, df: pl.DataFrame) -> "SlowPersistency":
        inst = cls(columns=df.columns)
        for i in range(df.shape[0]):
            inst.add(list(df.row(i)))

        inst.push_buffer()
        return inst

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

    def clean(self) -> None:
        clean_generated_path()

    def load(self) -> pl.DataFrame:
        if os.path.exists(self.path):
            return pl.read_csv(self.path)
        warnings.warn("CSV file not found")
        return pl.DataFrame([])

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, SlowPersistency):
            return False

        return bool(self.load().equals(value.load()))
