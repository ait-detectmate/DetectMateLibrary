import gc
import logging
import tempfile
from pathlib import Path

import pytest

import detectmatelibrary.schemas as schemas
from detectmatelibrary.common._core_op._train_buffer import TrainBuffer
from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode, DataBuffer

_MOD = "detectmatelibrary.common._core_op._train_buffer"


def _log(i: int) -> schemas.BaseSchema:
    # .copy() gives the BaseSchema that CoreComponent actually buffers
    return schemas.LogSchema({"logID": str(i), "logSource": "test", "hostname": "h"}).copy()


def _windows(n: int, size: int, start: int = 0) -> list[list[schemas.BaseSchema]]:
    """Sliding windows over logs start..start+n-1, as a WINDOW-mode
    CoreComponent buffers them."""
    data_buffer = DataBuffer(ArgsBuffer(BufferMode.WINDOW, size=size))
    return [w for w in (data_buffer.add(_log(i)) for i in range(start, start + n)) if w is not None]


def _count_serialize(monkeypatch) -> dict[str, int]:
    calls = {"n": 0}
    real = schemas.BaseSchema.serialize

    def counting(self):
        calls["n"] += 1
        return real(self)

    monkeypatch.setattr(schemas.BaseSchema, "serialize", counting)
    return calls


def _run_dirs(base: Path) -> list[Path]:
    return sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []


def _ids(records) -> list[str]:
    return [r["logID"] for r in records]


def _buffer(tmp_path: Path, max_records: int, window: int | None = None, name: str = "c") -> TrainBuffer:
    return TrainBuffer(
        schemas.LogSchema, max_records=max_records, spill_dir=str(tmp_path), window=window, name=name
    )


class TestInMemory:
    def test_replay_returns_same_objects_in_order_then_empties(self, tmp_path):
        buf = _buffer(tmp_path, max_records=10)
        records = [_log(i) for i in range(5)]
        for r in records:
            buf.add(r)
        out = list(buf)
        assert len(out) == 5
        assert all(a is b for a, b in zip(out, records))
        assert list(buf) == []
        assert _run_dirs(tmp_path) == []


class TestSpill:
    def test_spill_replays_all_records_in_order(self, tmp_path):
        buf = _buffer(tmp_path, max_records=3)
        for i in range(10):
            buf.add(_log(i))
        [run] = _run_dirs(tmp_path)
        assert run.name.startswith("detectmate-train-")
        assert len(list(run.glob("*.parquet"))) == 3
        out = list(buf)
        assert _ids(out) == [str(i) for i in range(10)]
        assert all(r.schema_class is schemas.LogSchema().schema_class for r in out)
        assert _run_dirs(tmp_path) == []

    def test_spilled_batches_replay_in_order(self, tmp_path):
        buf = _buffer(tmp_path, max_records=2)
        for i in range(5):
            buf.add([_log(2 * i), _log(2 * i + 1)])
        assert [_ids(b) for b in buf] == [[str(2 * i), str(2 * i + 1)] for i in range(5)]

    def test_sliding_windows_write_each_record_once(self, tmp_path, monkeypatch):
        windows = _windows(10, size=3)  # 8 windows: logs 0-2, 1-3, ..., 7-9
        calls = _count_serialize(monkeypatch)
        buf = _buffer(tmp_path, max_records=3, window=3)
        for w in windows:
            buf.add(w)
        # windows 0-5 are spilled, in two parts; together they hold logs 0-7
        assert calls["n"] == 8
        assert [_ids(w) for w in buf] == [[str(j) for j in range(i, i + 3)] for i in range(8)]

    @pytest.mark.parametrize("size", [1, 3])
    def test_spilled_windows_replay_in_order(self, tmp_path, size):
        buf = _buffer(tmp_path, max_records=2, window=size)
        for w in _windows(9, size=size):
            buf.add(w)
        assert [_ids(w) for w in buf] == [[str(j) for j in range(i, i + size)] for i in range(10 - size)]

    def test_first_spill_warns_once_with_the_dir(self, tmp_path, caplog):
        buf = _buffer(tmp_path, max_records=2)
        with caplog.at_level(logging.WARNING):
            for i in range(7):
                buf.add(_log(i))
        [run] = _run_dirs(tmp_path)
        warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert str(run) in warnings[0]

    @pytest.mark.parametrize("window", [None, 2])
    def test_buffer_is_reusable_after_replay(self, tmp_path, window):
        def records(start):
            return _windows(6, size=2, start=start) if window else [_log(i) for i in range(start, start + 5)]

        buf = _buffer(tmp_path, max_records=2, window=window)
        for r in records(0):
            buf.add(r)
        list(buf)
        second = records(100)
        for r in second:
            buf.add(r)
        assert list(buf) == second
        assert _run_dirs(tmp_path) == []

    def test_default_dir_is_the_system_temp_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
        buf = TrainBuffer(schemas.LogSchema, max_records=1, name="c")
        buf.add(_log(0))
        assert len(_run_dirs(tmp_path)) == 1
        assert _ids(buf) == ["0"]

    def test_missing_spill_dir_is_created(self, tmp_path):
        base = tmp_path / "not" / "yet"
        buf = _buffer(base, max_records=1)
        buf.add(_log(0))
        assert len(_run_dirs(base)) == 1
        assert _ids(buf) == ["0"]


class TestFailureModes:
    def test_failed_spill_raises_keeps_records_and_retries(self, tmp_path, monkeypatch):
        buf = _buffer(tmp_path, max_records=2)
        buf.add(_log(0))
        attempts = []

        def disk_full(*args, **kwargs):
            attempts.append(1)
            raise OSError("disk full")

        monkeypatch.setattr(f"{_MOD}.pq.write_table", disk_full)
        with pytest.raises(OSError):
            buf.add(_log(1))
        with pytest.raises(OSError):
            buf.add(_log(2))
        assert len(attempts) == 2
        monkeypatch.undo()
        buf.add(_log(3))
        assert _ids(buf) == ["0", "1", "2", "3"]

    def test_cleanup_error_warns_and_replay_completes(self, tmp_path, monkeypatch, caplog):
        buf = _buffer(tmp_path, max_records=2)
        for i in range(5):
            buf.add(_log(i))
        [run] = _run_dirs(tmp_path)

        def denied(self):
            raise PermissionError("denied")

        monkeypatch.setattr(tempfile.TemporaryDirectory, "cleanup", denied)
        with caplog.at_level(logging.WARNING):
            assert _ids(buf) == [str(i) for i in range(5)]
        assert any(str(run) in r.message for r in caplog.records if r.levelno == logging.WARNING)

    def test_dropped_buffer_removes_its_dir(self, tmp_path):
        buf = _buffer(tmp_path, max_records=2)
        for i in range(5):
            buf.add(_log(i))
        it = iter(buf)
        next(it)  # replay interrupted, e.g. train() raised
        assert len(_run_dirs(tmp_path)) == 1
        del it, buf
        gc.collect()
        assert _run_dirs(tmp_path) == []

    def test_two_buffers_sharing_a_dir_do_not_mix(self, tmp_path):
        a = _buffer(tmp_path, max_records=2, name="same")
        b = _buffer(tmp_path, max_records=2, name="same")
        for i in range(4):
            a.add(_log(i))
            b.add(_log(100 + i))
        assert len(_run_dirs(tmp_path)) == 2
        assert _ids(a) == ["0", "1", "2", "3"]
        assert _ids(b) == ["100", "101", "102", "103"]
