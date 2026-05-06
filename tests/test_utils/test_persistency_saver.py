import json
import time
import threading

import fsspec
import pytest

from detectmatelibrary.utils.persistency.event_data_structures.dataframes import EventDataFrame
from detectmatelibrary.utils.persistency.event_data_structures.trackers import EventStabilityTracker
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.persistency_saver import (
    PersistencySaverConfig,
    PersistencyLoadError,
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
        assert cfg.events_until_save is None
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

    def test_save_resets_events_since_save(self):
        saver, p = _memory_saver()
        assert p._events_since_save == 3
        saver.save()
        assert p._events_since_save == 0

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


class TestPersistencySaverTriggers:
    def test_timer_triggers_save(self):
        p = _make_persistency_with_data()
        cfg = PersistencySaverConfig(
            path="memory://trigger_test/state",
            save_interval_seconds=0,  # fire immediately
        )
        saver = PersistencySaver(p, cfg)
        saver.start()
        time.sleep(0.15)
        saver.stop()
        fs = fsspec.filesystem("memory")
        assert fs.exists("trigger_test/state/metadata.json")

    def test_timed_save_resets_events_since_save(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(
            path="memory://dirty_test2/state",
            save_interval_seconds=0,
        )
        saver = PersistencySaver(p, cfg)
        saver.start()

        p.ingest_event(event_id="E1", event_template="T", variables=["x"], named_variables={})
        p.ingest_event(event_id="E1", event_template="T", variables=["y"], named_variables={})
        time.sleep(0.15)
        saver.stop()

        assert p._events_since_save == 0  # save() was called by the timer, which resets the counter

    def test_stop_does_final_save(self):
        p = _make_persistency_with_data()
        cfg = PersistencySaverConfig(
            path="memory://stop_test/state",
            save_interval_seconds=9999,
        )
        saver = PersistencySaver(p, cfg)
        saver.start()
        saver.stop()
        fs = fsspec.filesystem("memory")
        assert fs.exists("stop_test/state/metadata.json")

    def test_auto_load_on_init(self):
        # First: save some state
        p1 = _make_persistency_with_data()
        PersistencySaver(p1, PersistencySaverConfig(path="memory://autoload/state")).save()

        # Then: create new persistency with auto_load=True
        p2 = EventPersistency(event_data_class=EventDataFrame)
        PersistencySaver(p2, PersistencySaverConfig(path="memory://autoload/state", auto_load=True))
        assert "E1" in p2.get_events_seen()


class TestPersistencySaverIntegration:
    def test_full_cycle_dataframe_backend(self):
        """Train → save → restore → verify data identical."""
        p1 = EventPersistency(event_data_class=EventDataFrame)
        for i in range(20):
            p1.ingest_event(
                event_id=f"E{i % 3}",
                event_template=f"Template {i % 3}",
                variables=[f"val_{i}"],
                named_variables={},
            )

        saver1 = PersistencySaver(p1, PersistencySaverConfig(path="memory://integration/df"))
        saver1.save()

        p2 = EventPersistency(event_data_class=EventDataFrame)
        PersistencySaver(p2, PersistencySaverConfig(path="memory://integration/df")).load()

        assert p2.get_events_seen() == p1.get_events_seen()
        assert p2.get_event_templates() == p1.get_event_templates()
        for eid in p1.get_events_data():
            original = p1.get_event_data(eid)
            restored = p2.get_event_data(eid)
            assert len(restored) == len(original)
            assert list(restored.columns) == list(original.columns)
            assert list(restored["var_0"]) == list(original["var_0"])

    def test_full_cycle_tracker_backend(self):
        """Train → save → restore → verify tracker state identical."""
        p1 = EventPersistency(event_data_class=EventStabilityTracker)
        for i in range(30):
            p1.ingest_event(
                event_id="E1",
                event_template="Tmpl",
                variables=[f"v_{i % 5}"],
                named_variables={},
            )

        saver1 = PersistencySaver(p1, PersistencySaverConfig(path="memory://integration/tracker"))
        saver1.save()

        p2 = EventPersistency(event_data_class=EventStabilityTracker)
        PersistencySaver(p2, PersistencySaverConfig(path="memory://integration/tracker")).load()

        original_tracker = p1.get_events_data()["E1"]
        restored_tracker = p2.get_events_data()["E1"]

        for var_name in original_tracker.get_variables():
            orig = original_tracker.get_data()[var_name]
            rest = restored_tracker.get_data()[var_name]
            assert list(rest.change_series) == list(orig.change_series)
            assert rest.unique_set == orig.unique_set
