import json
import time
import threading

import fsspec
import pytest

from detectmatelibrary.utils.persistency.event_data_structures.dataframes import EventDataFrame
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.exceptions import PersistencyLoadError
from detectmatelibrary.utils.persistency.persistency_saver import (
    PersistencySaverConfig,
    PersistencySaver,
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

        def inc():
            count["n"] += 1

        timer = _SaveTimer(interval=0.05, callback=inc)
        timer.start()
        time.sleep(0.12)
        timer.stop()
        timer.join(timeout=1.0)
        captured = count["n"]
        time.sleep(0.12)
        assert count["n"] == captured  # no more fires after stop


def _make_persistency_with_data() -> EventPersistency:
    p = EventPersistency(event_data_class=EventDataFrame)
    p.ingest_event(event_id="E1", event_template="User <*>", variables=["alice"], named_variables={})
    p.ingest_event(event_id="E1", event_template="User <*>", variables=["bob"], named_variables={})
    p.ingest_event(event_id="E2", event_template="Error <*>", variables=["timeout"], named_variables={})
    return p


def _memory_saver(path: str = "memory://test/state") -> tuple[PersistencySaver, EventPersistency]:
    p = _make_persistency_with_data()
    cfg = PersistencySaverConfig(path=path)
    saver = PersistencySaver(p, cfg)
    return saver, p


class TestPersistencySaverSaveLoad:
    def test_save_creates_metadata_json(self):
        saver, _ = _memory_saver()
        saver.save()
        fs = fsspec.filesystem("memory")
        assert fs.exists("test/state/metadata.json")

    def test_save_creates_event_files(self):
        saver, _ = _memory_saver()
        saver.save()
        fs = fsspec.filesystem("memory")
        assert fs.exists("test/state/events/E1.parquet")
        assert fs.exists("test/state/events/E2.parquet")

    def test_metadata_contains_events_seen(self):
        saver, _ = _memory_saver()
        saver.save()
        fs = fsspec.filesystem("memory")
        with fs.open("test/state/metadata.json", "r") as f:
            meta = json.load(f)
        assert set(meta["events_seen"]) == {"E1", "E2"}

    def test_save_resets_dirty_count(self):
        saver, p = _memory_saver()
        assert p._dirty_count == 3
        saver.save()
        assert p._dirty_count == 0

    def test_load_restores_events_seen(self):
        saver, _ = _memory_saver()
        saver.save()

        p2 = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(path="memory://test/state")
        saver2 = PersistencySaver(p2, cfg)
        saver2.load()
        assert "E1" in p2.get_events_seen()
        assert "E2" in p2.get_events_seen()

    def test_load_restores_event_data(self):
        saver, _ = _memory_saver()
        saver.save()

        p2 = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(path="memory://test/state")
        PersistencySaver(p2, cfg).load()
        assert len(p2.get_event_data("E1")) == 2

    def test_load_restores_templates(self):
        saver, _ = _memory_saver()
        saver.save()

        p2 = EventPersistency(event_data_class=EventDataFrame)
        PersistencySaver(p2, PersistencySaverConfig(path="memory://test/state")).load()
        assert p2.get_event_template("E1") == "User <*>"

    def test_load_raises_on_missing_path(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        saver = PersistencySaver(p, PersistencySaverConfig(path="memory://nonexistent/path"))
        with pytest.raises(PersistencyLoadError):
            saver.load()
