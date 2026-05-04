import time
import threading
from detectmatelibrary.utils.persistency.persistency_saver import (
    PersistencySaverConfig,
    _SaveTimer,
)


class TestPersistencySaverConfig:
    def test_requires_path(self):
        cfg = PersistencySaverConfig(path="file:///tmp/test")
        assert cfg.path == "file:///tmp/test"

    def test_defaults(self):
        cfg = PersistencySaverConfig(path="file:///tmp/test")
        assert cfg.save_interval_seconds == 300
        assert cfg.dirty_threshold == 1000
        assert cfg.auto_load is False
        assert cfg.storage_options == {}


class TestSaveTimer:
    def test_callback_fires_after_interval(self):
        fired = threading.Event()
        timer = _SaveTimer(interval=0.05, callback=fired.set)
        timer.start()
        assert fired.wait(timeout=1.0), "callback did not fire"
        timer.stop()
        timer.join(timeout=1.0)

    def test_stop_prevents_further_callbacks(self):
        count = {"n": 0}
        def inc(): count["n"] += 1
        timer = _SaveTimer(interval=0.05, callback=inc)
        timer.start()
        time.sleep(0.12)
        timer.stop()
        timer.join(timeout=1.0)
        captured = count["n"]
        time.sleep(0.12)
        assert count["n"] == captured  # no more fires after stop
