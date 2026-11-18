"""Tests for detectmatelibrary.utils.persistency.slow_persistency."""
from detectmatelibrary.utils.persistency.slow_persistency import (
    Manager, SlowPersistency, clean_generated_path, generate_path
)
import polars as pl
import os
import pathlib

import pytest


class TestSlowPersisntecy:
    def test_buffer(self) -> None:
        persistency = SlowPersistency(columns=[], file_manager=Manager, buffer_size=2)

        persistency.add(["a", 2])
        assert len(persistency.buffer) == 1

        persistency.add(["b", 1])
        assert len(persistency.buffer) == 0
        assert len(persistency.file_manager.test_buffer) == 3

        persistency.add(["c", 1])
        assert len(persistency.buffer) == 1
        assert len(persistency.file_manager.test_buffer) == 3

        persistency.push_buffer()
        assert len(persistency.buffer) == 0
        assert len(persistency.file_manager.test_buffer) == 4

    def test_csv_frame_file(self) -> None:
        persistency = SlowPersistency(columns=["char", "int"], buffer_size=2)
        persistency.add(["a", 2])
        persistency.add(["b", 2])

        assert os.path.exists(persistency.path)

        df = persistency.load()
        expected = pl.DataFrame({"char": ["a", "b"], "int": [2, 2]})
        assert df.equals(expected)

        persistency.reset()
        assert not os.path.exists(persistency.path)

    def test_transfer(self) -> None:
        persistency = SlowPersistency(columns=["char", "int"], buffer_size=2)
        persistency.add(["a", 2])
        persistency.add(["b", 2])

        df = persistency.load()

        assert len(df) == 2
        assert persistency == SlowPersistency.from_dataframe(df)

    def test_clean_generated_path_removes_the_generated_files_and_folder(self) -> None:
        # The test runs in its own working directory (tests/conftest.py).
        paths = [generate_path(), generate_path()]
        for path in paths:
            pathlib.Path(path).write_text("a,b\n")
        assert all(os.path.exists(path) for path in paths)

        clean_generated_path()

        assert not os.path.exists(".temp")

    def test_clean_generated_path_without_generated_files_does_nothing(self) -> None:
        clean_generated_path()
        assert not os.path.exists(".temp")


class TestSlowPersistencyEdgeCases:
    def test_load_before_anything_was_written_warns_and_is_empty(self):
        persistency = SlowPersistency(columns=["char"])
        with pytest.warns(UserWarning, match="CSV file not found"):
            assert persistency.load().is_empty()

    def test_only_another_slow_persistency_can_be_equal(self):
        assert SlowPersistency(columns=["char"]) != "not a store"
