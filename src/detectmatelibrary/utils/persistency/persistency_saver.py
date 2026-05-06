import atexit
import json
import signal
import threading
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
from tools.logging import logger

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


class PersistencyLoadError(Exception):
    """Raised when restoring persisted state fails."""


@dataclass
class PersistencySaverConfig:
    path: str
    save_interval_seconds: int = 300
    dirty_threshold: int = 1000
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
        self._lock = threading.Lock()
        self._timer: _SaveTimer | None = None

        if config.auto_load:
            self.load()

    def save(self) -> None:
        """Write full EventPersistency state to storage.

        Thread-safe.
        """
        with self._lock:
            try:
                self._fs.makedirs(f"{self._root}/events", exist_ok=True)
                event_backends: dict[str, str] = {}
                event_extensions: dict[str, str] = {}

                for event_id, data_structure in self._persistency.events_data.items():
                    backend_name = type(data_structure).__name__
                    ext = _EXTENSION_MAP.get(backend_name, "bin")
                    event_backends[str(event_id)] = backend_name
                    event_extensions[str(event_id)] = ext

                    file_path = f"{self._root}/events/{event_id}.{ext}"
                    with self._fs.open(file_path, "wb") as f:
                        f.write(data_structure.dump())

                metadata = {
                    "version": 1,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                    "events_seen": list(self._persistency.events_seen),
                    "event_templates": {
                        str(k): v for k, v in self._persistency.event_templates.items()
                    },
                    "event_backends": event_backends,
                    "event_extensions": event_extensions,
                    "event_data_kwargs": self._persistency.event_data_kwargs,
                }
                with self._fs.open(f"{self._root}/metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)

                self._persistency.reset_dirty_count()
            except Exception as e:
                logger.warning(f"PersistencySaver: save failed — {e}")

    def load(self) -> None:
        """Restore EventPersistency state from storage.

        Raises PersistencyLoadError on failure.
        """
        meta_path = f"{self._root}/metadata.json"
        if not self._fs.exists(meta_path):
            raise PersistencyLoadError(
                f"No saved state found at '{self._config.path}' (metadata.json missing)"
            )
        try:
            with self._fs.open(meta_path, "r") as f:
                metadata = json.load(f)

            self._persistency.events_seen = set(metadata["events_seen"])
            self._persistency.event_templates = {
                _coerce_event_id(k): v for k, v in metadata["event_templates"].items()
            }
            global_kwargs = metadata.get("event_data_kwargs", {})

            for event_id_str, backend_name in metadata["event_backends"].items():
                event_id = _coerce_event_id(event_id_str)
                ext = metadata["event_extensions"][event_id_str]
                file_path = f"{self._root}/events/{event_id_str}.{ext}"
                with self._fs.open(file_path, "rb") as f:
                    data = f.read()
                if backend_name not in _BACKEND_REGISTRY:
                    raise PersistencyLoadError(
                        f"Unknown backend '{backend_name}' — cannot restore event '{event_id}'"
                    )
                backend_cls = _BACKEND_REGISTRY[backend_name]
                self._persistency.events_data[event_id] = backend_cls.load(data, **global_kwargs)
        except PersistencyLoadError:
            raise
        except Exception as e:
            raise PersistencyLoadError(f"Failed to restore state: {e}") from e

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
        if self._timer is not None:
            self._timer.stop()
            self._timer.join(timeout=5.0)
            self._timer = None
        self.save()

    def _tick(self) -> None:
        """Called by the timer thread each interval."""
        # dirty_threshold reserved for future optimization
        self.save()
