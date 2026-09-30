"""Configure-phase records kept for training, spilled to disk when there are
many.

With ``use_config_data_as_training`` a component keeps every configure record
and replays it into ``train()`` once configuration ends. Up to ``max_records``
records stay in memory. Beyond that each full batch is written as one closed
Parquet part file through fsspec, and replay streams the parts back, so memory
stays bounded however long the configure phase is.
"""
import contextlib
import getpass
import os
import re
import stat
import tempfile
import uuid
import weakref
from typing import IO, Any, Iterator

import fsspec
from fsspec.implementations.local import LocalFileSystem

from detectmatelibrary.schemas import BaseSchema
from detectmatelibrary.tools.logging import logger

try:
    import fcntl
    _HAS_FLOCK = True
except ImportError:  # pragma: no cover - platforms without flock (Windows)
    _HAS_FLOCK = False

Record = BaseSchema | list[BaseSchema]

_COLUMN = "record"
_READ_BATCH = 10_000
_WRITE_SLICE = 10_000
_LOCK_NAME = re.compile(r"[A-Za-z0-9_-]+-[0-9a-f]{32}\.lock")
_PART_NAME = re.compile(r"part-\d{5}\.parquet")


def _safe_name(name: str) -> str:
    """Component name reduced to characters that are safe in a directory
    name."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", name) or "component"


def _user_tag() -> str:
    if hasattr(os, "getuid"):
        return str(os.getuid())
    try:
        return _safe_name(getpass.getuser())
    except OSError:
        return "user"


DEFAULT_TRAIN_BUFFER_DIR = os.path.join(
    tempfile.gettempdir(), f"detectmatelibrary-{_user_tag()}", "train_buffer"
)


def _is_own_dir(path: str) -> bool:
    """True if ``path`` is a real directory (not a symlink) owned by this
    user."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and (not hasattr(os, "getuid") or info.st_uid == os.getuid())


def _ensure_private_dir(path: str) -> None:
    """Create ``path`` with mode 0700 if missing; refuse one that is a symlink,
    not a directory, or owned by someone else."""
    os.makedirs(path, mode=0o700, exist_ok=True)
    if not _is_own_dir(path):
        raise PermissionError(
            f"The default train buffer directory {path} is a symlink, not a directory, or owned "
            "by another user, so the buffer will not spill there. Set train_buffer_dir to a "
            "directory you own."
        )


def _encode(rec: Record) -> bytes | list[bytes]:
    if isinstance(rec, list):
        return [r.serialize() for r in rec]
    return rec.serialize()


def _can_lock(fs: Any) -> bool:
    return _HAS_FLOCK and isinstance(fs, LocalFileSystem)


def _lock_run(base: str, stem: str) -> IO[str]:
    """Hold an exclusive flock on ``<base>/<stem>.lock`` while the run lives.

    The file is locked under a temporary name and then renamed, so a
    stale scan never finds an unlocked lock file that belongs to a live
    run.
    """
    os.makedirs(base, exist_ok=True)
    tmp = os.path.join(base, f"{stem}.lock.tmp")
    lock_file = open(tmp, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.replace(tmp, os.path.join(base, f"{stem}.lock"))
    except BaseException:
        lock_file.close()
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise
    return lock_file


def _remove_run(fs: Any, path: str, lock_file: IO[str] | None = None) -> None:
    removed = True
    try:
        fs.rm(path, recursive=True)
    except FileNotFoundError:
        pass  # nothing was spilled, or it is gone already
    except OSError as e:
        removed = False
        logger.warning(f"Could not remove train buffer files {path}: {e}. They can be deleted by hand.")
    if lock_file is not None:
        try:
            if removed:  # otherwise keep the lock so the next stale scan retries
                with contextlib.suppress(FileNotFoundError):
                    os.remove(f"{path}.lock")
        finally:
            lock_file.close()  # releases the flock only after the files are gone


class _RunDir:
    """The directory one spilling buffer writes its part files to."""

    def __init__(self, fs: Any, base: str, name: str) -> None:
        self.stem = f"{_safe_name(name)}-{uuid.uuid4().hex}"
        self.path = f"{base}/{self.stem}"
        lock_file = _lock_run(base, self.stem) if _can_lock(fs) else None
        try:
            if isinstance(fs, LocalFileSystem):
                os.makedirs(self.path, mode=0o700, exist_ok=True)
            else:
                fs.makedirs(self.path, exist_ok=True)
        except BaseException:
            if lock_file is not None:  # the run never existed: drop its lock
                with contextlib.suppress(OSError):
                    os.remove(f"{self.path}.lock")
                lock_file.close()
            raise
        # Also runs when the buffer is garbage-collected mid-configure, or at interpreter exit.
        self._finalizer = weakref.finalize(self, _remove_run, fs, self.path, lock_file)

    def remove(self) -> None:
        self._finalizer()


def remove_stale_runs(fs: Any, base: str) -> None:
    """Delete run directories whose process died without cleaning up (e.g.
    killed for running out of memory).

    A run is stale when its lock file can be locked: the kernel drops a
    dead process's flock, even after SIGKILL. Local disk with flock only.
    """
    if not _can_lock(fs):
        if isinstance(fs, LocalFileSystem):
            logger.debug("No fcntl here: train buffer runs are not locked and stale ones are not removed.")
        return
    if not os.path.isdir(base):
        return
    try:
        entries = os.listdir(base)
    except OSError:
        return  # base is not readable; skip gracefully
    for entry in entries:
        if _LOCK_NAME.fullmatch(entry):
            _remove_if_stale(os.path.join(base, entry))


def _remove_if_stale(lock_path: str) -> None:
    try:
        fd = os.open(lock_path, os.O_RDWR)
    except OSError:
        return  # gone already, or another user's file
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return  # a live process holds it
    try:
        run_path = lock_path[: -len(".lock")]
        left = False
        if os.path.isdir(run_path) and not os.path.islink(run_path):
            try:
                names = os.listdir(run_path)
            except OSError:
                names = []
            for name in names:
                if _PART_NAME.fullmatch(name):
                    with contextlib.suppress(OSError):
                        os.remove(os.path.join(run_path, name))
            try:
                os.rmdir(run_path)
            except OSError:
                left = True
        with contextlib.suppress(OSError):
            os.remove(lock_path)
        if left:
            logger.warning(
                f"Stale train buffer {run_path}: the process that wrote it ended without cleaning "
                "up, and the directory could not be removed (it holds other files, or the part "
                "files are not deletable). Delete it by hand."
            )
        else:
            logger.warning(
                f"Removed stale train buffer {run_path}: the process that wrote it ended without "
                "cleaning up (for example, killed while configuring)."
            )
    finally:
        os.close(fd)


class TrainBuffer:
    """Configure records in insertion order: in memory up to ``max_records``,
    then spilled to Parquet part files under ``dir_`` (an fsspec URI).

    Iterating replays every record once, in order, and empties the
    buffer.
    """

    def __init__(
        self,
        name: str = "component",
        max_records: int = 100_000,
        dir_: str | None = None,
        why: str | None = None,
    ) -> None:
        if max_records < 1:
            raise ValueError(f"max_records must be >= 1, got {max_records}")
        self.name = name
        self.max_records = max_records
        # Why the records are kept and how to avoid it, for the first-spill warning.
        self._why = why or (
            "With use_config_data_as_training=True every configure record is kept until training "
            f"starts, so the buffer now goes to disk in parts of {max_records} records and is read "
            "back when training starts. To avoid this, lower data_use_configure or set "
            "use_config_data_as_training=False."
        )
        self._fs: Any
        self._base: str
        self._default_dir = dir_ is None
        self._fs, self._base = fsspec.url_to_fs(dir_ or DEFAULT_TRAIN_BUFFER_DIR)
        self._memory: list[Record] = []
        self._parts: list[str] = []
        self._spill_at = max_records
        self._n_spilled = 0
        self._run: _RunDir | None = None
        self._schema_class: Any = None
        self._warned = False
        # Never clean up inside a default directory that another user could have planted.
        if not self._default_dir or _is_own_dir(os.path.dirname(DEFAULT_TRAIN_BUFFER_DIR)):
            remove_stale_runs(self._fs, self._base)

    def __len__(self) -> int:
        return self._n_spilled + len(self._memory)

    def __add__(self, elem: Record) -> "TrainBuffer":
        self.add(elem)
        return self

    def __iter__(self) -> Iterator[Record]:
        return self._replay()

    def add(self, elem: Record) -> None:
        self._memory.append(elem)
        if len(self._memory) >= self._spill_at:
            try:
                self._spill()
            except BaseException:
                self._spill_at += self.max_records  # back off instead of retrying on every add
                raise
            self._spill_at = self.max_records

    def clear(self) -> None:
        """Drop every record and delete the run directory, if any."""
        self._memory, self._parts, self._n_spilled = [], [], 0
        self._spill_at = self.max_records
        if self._run is not None:
            self._run.remove()
            self._run = None

    def _spill(self) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        if self._schema_class is None:
            first = self._memory[0]
            self._schema_class = (first[0] if isinstance(first, list) else first).schema_class
        if self._run is None:
            if self._default_dir:
                _ensure_private_dir(os.path.dirname(DEFAULT_TRAIN_BUFFER_DIR))
            self._run = _RunDir(self._fs, self._base, self.name)
            if not self._warned:
                self._warned = True
                logger.warning(
                    f"<<{self.name}>> the configure phase has buffered {self.max_records} records; "
                    f"spilling them to {self._run.path}. {self._why} Set train_buffer_dir to "
                    "choose where the files go."
                )
        is_list = isinstance(self._memory[0], list)
        type_ = pa.list_(pa.large_binary()) if is_list else pa.large_binary()
        path = f"{self._run.path}/part-{len(self._parts):05d}.parquet"
        with self._fs.open(path, "wb") as f:
            with pq.ParquetWriter(f, pa.schema([(_COLUMN, type_)]), compression="zstd") as writer:
                # Encode one slice at a time: a window record is many serialized schemas.
                for i in range(0, len(self._memory), _WRITE_SLICE):
                    encoded = [_encode(rec) for rec in self._memory[i:i + _WRITE_SLICE]]
                    writer.write_table(pa.table({_COLUMN: pa.array(encoded, type=type_)}))
                    del encoded
        # Forget the records only once their part file is complete.
        self._parts.append(path)
        self._n_spilled += len(self._memory)
        self._memory = []

    def _replay(self) -> Iterator[Record]:
        import pyarrow.parquet as pq

        for path in self._parts:
            with self._fs.open(path, "rb") as f:
                batches = pq.ParquetFile(f).iter_batches(batch_size=_READ_BATCH, columns=[_COLUMN])
                for batch in batches:
                    for value in batch.column(0).to_pylist():
                        yield self._decode(value)
        yield from self._memory
        self.clear()

    def _decode(self, value: bytes | list[bytes]) -> Record:
        if isinstance(value, list):
            return [self._schema(v) for v in value]
        return self._schema(value)

    def _schema(self, message: bytes) -> BaseSchema:
        record = BaseSchema(schema_class=self._schema_class)
        record.deserialize(message)
        return record
