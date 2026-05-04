import threading
from dataclasses import dataclass, field
from typing import Any, Callable


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
