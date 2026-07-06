import atexit
import io
import json
import signal
import threading
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import fsspec

from detectmatelibrary.utils.persistency.event_data_structures.base import EventDataStructure
from detectmatelibrary.utils.persistency.event_data_structures.dataframes import (
    EventDataFrame,
    ChunkedEventDataFrame,
)
from detectmatelibrary.utils.persistency.event_data_structures.trackers import (
    EventTracker,
    EventStabilityTracker,
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.tools.logging import logger

_BACKEND_REGISTRY: dict[str, type[EventDataStructure]] = {
    "EventTracker": EventTracker,
    "EventStabilityTracker": EventStabilityTracker,
    "EventDataFrame": EventDataFrame,
    "ChunkedEventDataFrame": ChunkedEventDataFrame,
}

_EXTENSION_MAP: dict[str, str] = {
    "EventTracker": "msgpack",
    "EventStabilityTracker": "msgpack",
    "EventDataFrame": "parquet",
    "ChunkedEventDataFrame": "parquet",
}


def _coerce_event_id(k: str) -> int | str:
    try:
        return int(k)
    except ValueError:
        return k


def _safe_event_data_kwargs(ep: EventPersistency) -> dict[str, Any]:
    safe = {}
    for k, v in ep.event_data_kwargs.items():
        try:
            json.dumps(v)
            safe[k] = v
        except (TypeError, ValueError):
            logger.debug("Skipping non-JSON-serializable event_data_kwargs[%r]", k)
    return safe


def _serialize(ep: EventPersistency) -> dict[str, bytes]:
    """Serialize EP state to {relative_path: bytes}.

    Pure CPU — reads live ep state, does no I/O and does NOT reset the
    events-since-save counter. Callers that persist a save reset the
    counter themselves (see PersistencySaver.save).
    """
    files: dict[str, bytes] = {}
    event_backends: dict[str, str] = {}
    event_extensions: dict[str, str] = {}

    for event_id, data_structure in ep.events_data.items():
        backend_name = type(data_structure).__name__
        ext = _EXTENSION_MAP.get(backend_name, "bin")
        event_backends[str(event_id)] = backend_name
        event_extensions[str(event_id)] = ext
        files[f"events/{event_id}.{ext}"] = data_structure.dump()

    metadata = {
        "version": 1,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "events_seen": list(ep.events_seen),
        "event_templates": {str(k): v for k, v in ep.event_templates.items()},
        "event_backends": event_backends,
        "event_extensions": event_extensions,
        "event_data_kwargs": _safe_event_data_kwargs(ep),
        "event_data_class": ep.event_data_class.__name__,  # read back by _load
    }
    files["metadata.json"] = json.dumps(metadata, indent=2).encode()
    return files


def _write(fs: Any, root: str, files: dict[str, bytes]) -> None:
    """Write serialized files to storage.

    Pure I/O.
    """
    fs.makedirs(f"{root}/events", exist_ok=True)
    for rel, data in files.items():
        fs.pipe(f"{root}/{rel}", data)


def _save(ep: EventPersistency, fs: Any, root: str) -> None:
    # No counter reset here — that is a PersistencySaver concern (see save()).
    _write(fs, root, _serialize(ep))


class PersistencyLoadError(Exception):
    """Raised when restoring persisted state fails."""


def _load(ep: EventPersistency, fs: Any, root: str) -> None:
    meta_path = f"{root}/metadata.json"
    if not fs.exists(meta_path):
        raise PersistencyLoadError(
            f"No saved state found at '{root}' (metadata.json missing)"
        )
    try:
        with fs.open(meta_path, "r") as f:
            metadata = json.load(f)

        ep.events_data = {}
        ep.event_templates = {}

        ep.events_seen = set(metadata["events_seen"])
        ep.event_templates = {
            _coerce_event_id(k): v for k, v in metadata["event_templates"].items()
        }
        global_kwargs = metadata.get("event_data_kwargs", {})
        ep.event_data_kwargs = global_kwargs

        for event_id_str, backend_name in metadata["event_backends"].items():
            event_id = _coerce_event_id(event_id_str)
            ext = metadata["event_extensions"][event_id_str]
            file_path = f"{root}/events/{event_id_str}.{ext}"
            with fs.open(file_path, "rb") as f:
                data = f.read()
            if backend_name not in _BACKEND_REGISTRY:
                raise PersistencyLoadError(
                    f"Unknown backend '{backend_name}' — cannot restore event '{event_id}'"
                )
            backend_cls = _BACKEND_REGISTRY[backend_name]
            ep.events_data[event_id] = backend_cls.load(data, **global_kwargs)

        class_name = metadata.get("event_data_class")
        if class_name and class_name in _BACKEND_REGISTRY:
            ep.event_data_class = _BACKEND_REGISTRY[class_name]
    except PersistencyLoadError:
        raise
    except Exception as e:
        raise PersistencyLoadError(f"Failed to restore state: {e}") from e


def _save_to_bytes(ep: EventPersistency) -> bytes:
    """Serialize EP state to a zip archive in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel, data in _serialize(ep).items():
            zf.writestr(rel, data)
    return buf.getvalue()


def _load_from_bytes(ep: EventPersistency, data: bytes) -> None:
    """Restore EP state from a zip archive in memory."""
    # reusing the same _save logic with an in-memory filesystem to avoid code duplication
    from fsspec.implementations.memory import MemoryFileSystem
    mem_fs = MemoryFileSystem()
    root = "s"
    mem_fs.makedirs(f"{root}/events", exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            mem_fs.pipe(f"{root}/{name}", zf.read(name))
    _load(ep, mem_fs, root)


@dataclass
class PersistencySaverConfig:
    path: str
    save_interval_seconds: int = 300
    events_until_save: int | None = None
    auto_load: bool = False
    storage_options: dict[str, Any] = field(default_factory=dict)


class _SaveTimer(threading.Thread):
    """Daemon thread that calls callback every interval seconds."""

    def __init__(self, interval: float, callback: Callable[[], None]) -> None:
        super().__init__(daemon=True)
        self._interval = interval
        self._callback = callback
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._callback()

    def stop(self) -> None:
        self._stop_event.set()


class PersistencySaver:
    """Saves and restores EventPersistency state to/from configurable storage
    via fsspec."""

    def __init__(self, persistency: EventPersistency, config: PersistencySaverConfig) -> None:
        self._persistency = persistency
        self._config = config
        self._fs, self._root = fsspec.url_to_fs(config.path, **config.storage_options)
        # Share the EventPersistency lock so save/load are mutually exclusive
        # with ingest_event (which holds the same lock).
        self._lock = persistency._lock
        self._timer: _SaveTimer | None = None

        if config.events_until_save is not None:
            persistency.register_on_ingest(self._check_event_count)

        if config.auto_load:
            try:
                self.load()
            except PersistencyLoadError as e:
                logger.info(f"PersistencySaver: auto_load enabled but no state found, start fresh.({e})")

    def save(self) -> None:
        """Write full EventPersistency state to storage.

        Thread-safe. Serialization runs under the shared lock (reads
        live state); the file write runs outside it so ingest_event
        isn't blocked on I/O.
        """
        with self._lock:
            files = _serialize(self._persistency)
            # Reset here (atomically with the snapshot) not in _serialize:
            # module-level save()/export must not touch the save counter.
            self._persistency.reset_events_since_save()
        try:
            _write(self._fs, self._root, files)
        except Exception as e:
            logger.warning(f"PersistencySaver: save failed — {e}")

    def load(self) -> None:
        """Restore EventPersistency state from storage.

        Raises PersistencyLoadError on failure.
        """
        with self._lock:
            _load(self._persistency, self._fs, self._root)

    def start(self) -> None:
        """Start the background save timer and register process-exit hooks."""
        atexit.register(self.stop)
        try:
            signal.signal(signal.SIGTERM, lambda *_: self.stop())
        except (OSError, ValueError):
            pass  # not the main thread or signal not available

        self._timer = _SaveTimer(
            interval=self._config.save_interval_seconds,
            callback=self._tick,
        )
        self._timer.start()

    def stop(self) -> None:
        """Stop the timer and do a final save."""
        if self._timer is None:
            return
        self._timer.stop()
        self._timer.join(timeout=5.0)
        self._timer = None
        atexit.unregister(self.stop)
        self.save()

    def get_status(self) -> dict[str, Any]:
        """Return a snapshot of the current persistency state.

        Reads last_saved_at from metadata.json if present. A missing or
        unreadable metadata file is tolerated
        """
        ep = self._persistency
        last_saved_at: str | None = None
        try:
            meta_path = f"{self._root}/metadata.json"
            if self._fs.exists(meta_path):
                with self._fs.open(meta_path, "r") as f:
                    meta = json.load(f)
                last_saved_at = meta.get("saved_at")
        except Exception as e:
            logger.warning(f"PersistencySaver.get_status: could not read metadata.json — {e}")
        return {
            "path": self._config.path,
            "save_interval_seconds": self._config.save_interval_seconds,
            "events_until_save": self._config.events_until_save,
            "auto_load": self._config.auto_load,
            "events_seen_count": len(ep.get_events_seen()),
            "events_with_data_count": len(ep.get_events_data()),
            "events_since_save": ep.events_since_save,
            "last_saved_at": last_saved_at,
        }

    @contextmanager
    def locked(self) -> Any:
        """Context manager that acquires the internal save lock."""
        with self._lock:
            yield

    def _check_event_count(self) -> None:
        """Trigger a save when ingested-event count reaches
        events_until_save."""
        # ponytail: this runs OUTSIDE the ingest lock (callbacks fire after the
        # lock releases) so save()'s file I/O never stalls ingest. The counter
        # read is intentionally lock-free — a TOCTOU race here only ever causes a
        # slightly-late or redundant save, never a missed save or lost event
        # (events stay in memory until persisted). Do NOT re-add a lock around
        # this: it would put save's I/O back under the ingest lock.
        if (
            self._config.events_until_save is not None
            and self._persistency._events_since_save >= self._config.events_until_save
        ):
            self.save()

    def _tick(self) -> None:
        """Called by the timer thread each interval."""
        self.save()


def save(
    ep: EventPersistency,
    path: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> bytes | None:
    """Save EventPersistency state to an fsspec URI or return bytes.

    When path is None, serialises state to a zip archive and returns the
    bytes — no filesystem I/O occurs.  When path is given, writes to
    that URI and returns None.

    Not thread-safe when called concurrently with a running
    PersistencySaver on the same ep. Use CoreComponent.export_state() in
    that case.
    """
    if path is None:
        return _save_to_bytes(ep)
    fs, root = fsspec.url_to_fs(path, **(storage_options or {}))
    _save(ep, fs, root)
    return None


def load(
    ep: EventPersistency,
    path: str | bytes,
    storage_options: dict[str, Any] | None = None,
) -> None:
    """Restore EventPersistency state from an fsspec URI or bytes.

    When path is bytes (a zip archive returned by save()), state is
    restored directly from memory — no filesystem I/O occurs.  When path
    is a string URI, state is read from that location.

    Raises PersistencyLoadError if no saved state exists at path. Not
    thread-safe when called concurrently with a running PersistencySaver
    on the same ep. Use CoreComponent.import_state() in that case.
    """
    if isinstance(path, bytes):
        _load_from_bytes(ep, path)
        return
    fs, root = fsspec.url_to_fs(path, **(storage_options or {}))
    _load(ep, fs, root)
