import gc
import logging
import os
import stat
import subprocess
import sys

import fsspec
import pytest

import detectmatelibrary.common._core_op._train_buffer as tb
import detectmatelibrary.schemas as schemas
from detectmatelibrary.common._core_op._train_buffer import TrainBuffer


def _log(i: int) -> schemas.BaseSchema:
    # .copy() gives the BaseSchema that CoreComponent actually buffers
    return schemas.LogSchema({"logID": str(i), "logSource": "test", "hostname": "h"}).copy()


def _run_dirs(base) -> list[str]:
    if not os.path.isdir(base):
        return []
    return sorted(e for e in os.listdir(base) if os.path.isdir(os.path.join(base, e)))


def _ids(records) -> list[str]:
    return [r["logID"] for r in records]


class TestInMemory:
    def test_replay_returns_same_objects_in_order(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=10, dir_=str(tmp_path))
        records = [_log(i) for i in range(5)]
        for r in records:
            buf.add(r)
        assert len(buf) == 5
        out = list(buf)
        assert len(out) == 5
        assert all(a is b for a, b in zip(out, records))
        assert len(buf) == 0
        assert _run_dirs(tmp_path) == []

    def test_add_operator_kept_for_compat(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=10, dir_=str(tmp_path))
        buf + _log(0)
        assert len(buf) == 1

    def test_rejects_non_positive_max_records(self):
        with pytest.raises(ValueError):
            TrainBuffer(max_records=0)


class TestSpill:
    def test_spill_replays_all_records_in_order(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=3, dir_=str(tmp_path))
        records = [_log(i) for i in range(10)]
        for r in records:
            buf.add(r)
        assert len(buf) == 10
        [run] = _run_dirs(tmp_path)
        assert sorted(os.listdir(tmp_path / run)) == [
            "part-00000.parquet", "part-00001.parquet", "part-00002.parquet"
        ]
        out = list(buf)
        assert out == records
        assert _ids(out) == [str(i) for i in range(10)]
        assert out[0].schema_class is records[0].schema_class
        assert len(buf) == 0
        assert _run_dirs(tmp_path) == []

    def test_spill_window_lists(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=2, dir_=str(tmp_path))
        windows = [[_log(i), _log(i + 1)] for i in range(5)]
        for w in windows:
            buf.add(w)
        out = list(buf)
        assert out == windows
        assert all(isinstance(w, list) and len(w) == 2 for w in out)

    def test_first_spill_warns_once(self, tmp_path, caplog):
        buf = TrainBuffer(name="c", max_records=2, dir_=str(tmp_path))
        with caplog.at_level(logging.WARNING):
            for i in range(7):
                buf.add(_log(i))
        msgs = [r.message for r in caplog.records if "use_config_data_as_training" in r.message]
        assert len(msgs) == 1
        assert "spilling them to" in msgs[0]
        assert "data_use_configure" in msgs[0]
        assert "train_buffer_dir" in msgs[0]

    def test_first_spill_warning_gives_the_callers_reason(self, tmp_path, caplog):
        buf = TrainBuffer(name="c", max_records=2, dir_=str(tmp_path), why="Kept for pass two.")
        with caplog.at_level(logging.WARNING):
            for i in range(3):
                buf.add(_log(i))
        msgs = [r.message for r in caplog.records if "spilling them to" in r.message]
        assert len(msgs) == 1
        assert "Kept for pass two." in msgs[0]
        assert "use_config_data_as_training" not in msgs[0]
        assert "train_buffer_dir" in msgs[0]

    def test_buffer_is_reusable_after_replay(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=2, dir_=str(tmp_path))
        for i in range(5):
            buf.add(_log(i))
        list(buf)
        for i in range(5, 10):
            buf.add(_log(i))
        assert _ids(buf) == [str(i) for i in range(5, 10)]
        assert _run_dirs(tmp_path) == []

    def test_memory_filesystem(self):
        fs = fsspec.filesystem("memory")
        buf = TrainBuffer(name="c", max_records=2, dir_="memory://dml-train-buffer-test")
        for i in range(5):
            buf.add(_log(i))
        assert fs.ls("/dml-train-buffer-test")
        assert _ids(buf) == [str(i) for i in range(5)]
        assert not fs.exists("/dml-train-buffer-test") or fs.ls("/dml-train-buffer-test") == []

    @pytest.mark.parametrize("window", [False, True])
    def test_sliced_write_replays_in_order(self, tmp_path, monkeypatch, window):
        monkeypatch.setattr(tb, "_WRITE_SLICE", 3)
        buf = TrainBuffer(name="c", max_records=10, dir_=str(tmp_path))
        records = [[_log(i), _log(i + 1)] if window else _log(i) for i in range(25)]
        for r in records:
            buf.add(r)
        assert len(os.listdir(tmp_path / _run_dirs(tmp_path)[0])) == 2
        assert list(buf) == records

    def test_non_schema_records_stay_in_memory(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=10, dir_=str(tmp_path))
        for i in range(5):
            buf.add(i)
        assert list(buf) == [0, 1, 2, 3, 4]


class TestPrivateDefaultDir:
    def test_default_dir_has_user_tag(self):
        assert f"detectmatelibrary-{os.getuid()}" in tb.DEFAULT_TRAIN_BUFFER_DIR

    def test_local_run_dir_is_private(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=1, dir_=str(tmp_path))
        buf.add(_log(0))
        [run] = _run_dirs(tmp_path)
        assert stat.S_IMODE(os.stat(tmp_path / run).st_mode) == 0o700
        list(buf)

    def test_symlinked_top_dir_is_refused(self, tmp_path, monkeypatch):
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        os.symlink(elsewhere, tmp_path / "top")
        monkeypatch.setattr(tb, "DEFAULT_TRAIN_BUFFER_DIR", str(tmp_path / "top" / "train_buffer"))
        buf = TrainBuffer(max_records=2)
        buf.add(_log(0))
        with pytest.raises(PermissionError, match="train_buffer_dir"):
            buf.add(_log(1))
        assert os.listdir(elsewhere) == []
        assert _ids(buf) == ["0", "1"]

    def test_no_stale_scan_in_symlinked_top_dir(self, tmp_path, monkeypatch):
        elsewhere = tmp_path / "elsewhere"
        stale = TestStaleCleanup._stale_run(elsewhere / "train_buffer")
        os.symlink(elsewhere, tmp_path / "top")
        monkeypatch.setattr(tb, "DEFAULT_TRAIN_BUFFER_DIR", str(tmp_path / "top" / "train_buffer"))
        TrainBuffer()
        assert (stale / "part-00000.parquet").exists()

    def test_default_dir_is_created_private(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tb, "DEFAULT_TRAIN_BUFFER_DIR", str(tmp_path / "top" / "train_buffer"))
        buf = TrainBuffer(max_records=2)
        for i in range(3):
            buf.add(_log(i))
        assert stat.S_IMODE(os.stat(tmp_path / "top").st_mode) == 0o700
        assert _ids(buf) == ["0", "1", "2"]


class TestFailureModes:
    def test_failed_spill_keeps_records_and_raises(self, tmp_path, monkeypatch):
        buf = TrainBuffer(name="c", max_records=3, dir_=str(tmp_path))
        for i in range(2):
            buf.add(_log(i))

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(buf._fs, "open", boom)
        with pytest.raises(OSError):
            buf.add(_log(2))
        monkeypatch.undo()
        assert len(buf) == 3
        assert _ids(buf) == ["0", "1", "2"]

    def test_failed_spill_backs_off(self, tmp_path, monkeypatch):
        buf = TrainBuffer(name="c", max_records=3, dir_=str(tmp_path))
        real_open = buf._fs.open
        state = {"fail": True, "attempts": 0}

        def flaky(path, mode="rb", **kwargs):
            if "w" in mode:
                state["attempts"] += 1
                if state["fail"]:
                    raise OSError("disk full")
            return real_open(path, mode, **kwargs)

        monkeypatch.setattr(buf._fs, "open", flaky)
        for i in range(2):
            buf.add(_log(i))
        with pytest.raises(OSError):
            buf.add(_log(2))  # threshold 3
        buf.add(_log(3))
        buf.add(_log(4))
        assert state["attempts"] == 1  # adds 4 and 5 did not retry
        with pytest.raises(OSError):
            buf.add(_log(5))  # threshold 6
        assert state["attempts"] == 2
        state["fail"] = False
        buf.add(_log(6))
        buf.add(_log(7))
        assert state["attempts"] == 2
        buf.add(_log(8))  # threshold 9
        assert state["attempts"] == 3
        monkeypatch.undo()
        assert len(buf) == 9
        assert _ids(buf) == [str(i) for i in range(9)]

    def test_cleanup_error_does_not_abort_replay(self, tmp_path, monkeypatch, caplog):
        buf = TrainBuffer(name="c", max_records=2, dir_=str(tmp_path))
        for i in range(5):
            buf.add(_log(i))
        [run] = _run_dirs(tmp_path)

        def denied(*args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr(buf._fs, "rm", denied)
        with caplog.at_level(logging.WARNING):
            assert _ids(buf) == [str(i) for i in range(5)]
        assert any("by hand" in r.message for r in caplog.records)
        lock = tmp_path / f"{run}.lock"
        assert lock.exists()
        with open(lock, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)  # no longer held

    def test_unsafe_name_stays_inside_base(self, tmp_path):
        base = tmp_path / "base"
        buf = TrainBuffer(name="../a/b c", max_records=1, dir_=str(base))
        buf.add(_log(0))
        [run] = _run_dirs(base)
        assert run.startswith("___a_b_c-")
        assert not (tmp_path / "a").exists()

    def test_two_buffers_same_name_do_not_mix(self, tmp_path):
        a = TrainBuffer(name="same", max_records=2, dir_=str(tmp_path))
        b = TrainBuffer(name="same", max_records=2, dir_=str(tmp_path))
        for i in range(4):
            a.add(_log(i))
            b.add(_log(100 + i))
        assert len(_run_dirs(tmp_path)) == 2
        assert _ids(a) == ["0", "1", "2", "3"]
        assert _ids(b) == ["100", "101", "102", "103"]

    def test_dropped_buffer_removes_its_run_dir(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=2, dir_=str(tmp_path))
        for i in range(5):
            buf.add(_log(i))
        it = iter(buf)
        next(it)  # replay interrupted, e.g. train() raised
        assert len(_run_dirs(tmp_path)) == 1
        del it, buf
        gc.collect()
        assert _run_dirs(tmp_path) == []


fcntl = pytest.importorskip("fcntl")


class TestStaleCleanup:
    @staticmethod
    def _stale_run(base, stem="old-" + "0" * 32):
        os.makedirs(base / stem)
        (base / stem / "part-00000.parquet").write_bytes(b"x")
        (base / f"{stem}.lock").write_text("")
        return base / stem

    def test_stale_run_dir_is_removed_at_init(self, tmp_path, caplog):
        run = self._stale_run(tmp_path)
        with caplog.at_level(logging.WARNING):
            TrainBuffer(name="c", dir_=str(tmp_path))
        assert not run.exists()
        assert not (tmp_path / "old-00000000000000000000000000000000.lock").exists()
        assert any("stale" in r.message for r in caplog.records)

    def test_stale_cleanup_leaves_foreign_files(self, tmp_path):
        run = self._stale_run(tmp_path)
        (run / "notes.txt").write_text("keep")
        TrainBuffer(name="c", dir_=str(tmp_path))
        assert not (run / "part-00000.parquet").exists()
        assert (run / "notes.txt").exists()
        assert not (tmp_path / "old-00000000000000000000000000000000.lock").exists()

    def test_locked_run_dir_is_kept(self, tmp_path):
        run = self._stale_run(tmp_path)
        with open(tmp_path / "old-00000000000000000000000000000000.lock", "r+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            TrainBuffer(name="c", dir_=str(tmp_path))
            assert run.exists()

    def test_live_buffer_holds_its_lock(self, tmp_path):
        buf = TrainBuffer(name="c", max_records=1, dir_=str(tmp_path))
        buf.add(_log(0))
        [run] = _run_dirs(tmp_path)
        assert (tmp_path / f"{run}.lock").exists()
        TrainBuffer(name="other", dir_=str(tmp_path))  # scans; must not touch the live run
        assert _run_dirs(tmp_path) == [run]
        assert _ids(buf) == ["0"]
        assert not (tmp_path / f"{run}.lock").exists()

    def test_unreadable_lock_file_is_skipped(self, tmp_path):
        if os.geteuid() == 0:
            pytest.skip("root can open any file")
        run = self._stale_run(tmp_path)
        os.chmod(tmp_path / "old-00000000000000000000000000000000.lock", 0)
        try:
            TrainBuffer(name="c", dir_=str(tmp_path))
            assert run.exists()
        finally:
            os.chmod(tmp_path / "old-00000000000000000000000000000000.lock", 0o600)

    def test_killed_process_run_dir_is_removed(self, tmp_path):
        code = (
            "import os, signal\n"
            "import detectmatelibrary.schemas as s\n"
            "from detectmatelibrary.common._core_op._train_buffer import TrainBuffer\n"
            f"b = TrainBuffer(name='victim', max_records=1, dir_={str(tmp_path)!r})\n"
            "b.add(s.LogSchema({'logID': '0'}).copy())\n"
            "os.kill(os.getpid(), signal.SIGKILL)\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], timeout=60)
        assert proc.returncode == -9
        [run] = _run_dirs(tmp_path)
        assert (tmp_path / f"{run}.lock").exists()
        TrainBuffer(name="c", dir_=str(tmp_path))
        assert _run_dirs(tmp_path) == []
        assert not (tmp_path / f"{run}.lock").exists()

    def test_unrelated_lock_files_are_ignored(self, tmp_path):
        # Create unrelated files that should not be touched
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "model.bin").write_bytes(b"model")
        (tmp_path / "results.lock").write_text("")
        (tmp_path / "uv.lock").write_text("")
        TrainBuffer(name="c", dir_=str(tmp_path))
        assert results_dir.exists()
        assert (results_dir / "model.bin").exists()
        assert (tmp_path / "results.lock").exists()
        assert (tmp_path / "uv.lock").exists()

    def test_unreadable_base_does_not_crash(self, tmp_path):
        if os.geteuid() == 0:
            pytest.skip("root can open any file")
        base = tmp_path / "base"
        base.mkdir()
        os.chmod(base, 0o300)
        try:
            TrainBuffer(name="c", dir_=str(base))
        finally:
            os.chmod(base, 0o700)
