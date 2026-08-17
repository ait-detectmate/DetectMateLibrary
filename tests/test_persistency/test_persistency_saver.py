import json
import time
import threading

import fsspec
import pytest

from detectmatelibrary.utils.persistency.event_data_structures.dataframes import (
    EventDataFrame,
    ChunkedEventDataFrame,
)
from detectmatelibrary.utils.persistency.event_data_structures.trackers import EventStabilityTracker
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.persistency_saver import (
    PersistencySaverConfig,
    PersistencyLoadError,
    PersistencySaver,
    _SaveTimer,
    save as standalone_save,
    load as standalone_load,
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

    def test_save_includes_event_data_class_in_metadata(self):
        saver, _ = _memory_saver()
        saver.save()
        fs = fsspec.filesystem("memory")
        with fs.open("test/state/metadata.json", "r") as f:
            meta = json.load(f)
        assert meta["event_data_class"] == "EventDataFrame"

    def test_load_restores_event_data_class(self):
        saver, _ = _memory_saver()
        saver.save()
        # Start with a different class to verify it gets overwritten
        p2 = EventPersistency(event_data_class=EventStabilityTracker)
        PersistencySaver(p2, PersistencySaverConfig(path="memory://test/state")).load()
        assert p2.event_data_class is EventDataFrame

    def test_load_clears_stale_events_data(self):
        """Loading into a non-empty EP must replace, not merge, events_data."""
        saver, _ = _memory_saver()
        saver.save()  # saves E1 and E2

        p2 = EventPersistency(event_data_class=EventDataFrame)
        # Pre-populate with a key NOT in the saved snapshot
        p2.ingest_event(event_id="STALE", event_template="stale", variables=["x"], named_variables={})
        PersistencySaver(p2, PersistencySaverConfig(path="memory://test/state")).load()

        assert "STALE" not in p2.get_events_data()
        assert "E1" in p2.get_events_data()

    def test_load_restores_event_data_kwargs(self):
        """event_data_kwargs must be written back to ep after load."""
        p = EventPersistency(
            event_data_class=ChunkedEventDataFrame,
            event_data_kwargs={"max_rows": 500},
        )
        p.ingest_event(event_id="E1", event_template="t", variables=["v"], named_variables={})
        saver = PersistencySaver(p, PersistencySaverConfig(path="memory://kwargs_test/state"))
        saver.save()

        p2 = EventPersistency(event_data_class=ChunkedEventDataFrame)  # no kwargs
        PersistencySaver(p2, PersistencySaverConfig(path="memory://kwargs_test/state")).load()
        assert p2.event_data_kwargs == {"max_rows": 500}


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

    def test_events_until_save_triggers_save(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(
            path="memory://events_count_test/state",
            save_interval_seconds=9999,
            events_until_save=3,
        )
        PersistencySaver(p, cfg)  # no start() needed — callback fires on ingest
        for i in range(3):
            p.ingest_event(event_id="E1", event_template="T", variables=[str(i)], named_variables={})
        fs = fsspec.filesystem("memory")
        assert fs.exists("events_count_test/state/metadata.json")

    def test_events_until_save_no_save_before_threshold(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(
            path="memory://events_count_test2/state",
            save_interval_seconds=9999,
            events_until_save=5,
        )
        PersistencySaver(p, cfg)
        for i in range(4):
            p.ingest_event(event_id="E1", event_template="T", variables=[str(i)], named_variables={})
        fs = fsspec.filesystem("memory")
        assert not fs.exists("events_count_test2/state/metadata.json")

    def test_events_until_save_resets_counter_and_retrigggers(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(
            path="memory://events_count_test3/state",
            save_interval_seconds=9999,
            events_until_save=2,
        )
        PersistencySaver(p, cfg)
        for i in range(4):
            p.ingest_event(event_id="E1", event_template="T", variables=[str(i)], named_variables={})
        # counter should be 0 — two saves fired (at event 2 and event 4)
        assert p._events_since_save == 0

    def test_auto_load_on_init(self):
        # First: save some state
        p1 = _make_persistency_with_data()
        PersistencySaver(p1, PersistencySaverConfig(path="memory://autoload/state")).save()

        # Then: create new persistency with auto_load=True
        p2 = EventPersistency(event_data_class=EventDataFrame)
        PersistencySaver(p2, PersistencySaverConfig(path="memory://autoload/state", auto_load=True))
        assert "E1" in p2.get_events_seen()

    def test_auto_load_on_init_no_state_starts_fresh(self):
        # auto_load=True with no prior save must not crash but starts with empty state
        p = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(path="memory://autoload_no_prior_state/state", auto_load=True)
        saver = PersistencySaver(p, cfg)
        assert len(p.get_events_seen()) == 0
        assert len(p.get_events_data()) == 0
        assert saver is not None


class TestPersistencySaverGetStatus:
    def test_config_fields(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        cfg = PersistencySaverConfig(
            path="memory://status_test3/state",
            save_interval_seconds=120,
            events_until_save=500,
            auto_load=True,
        )
        saver = PersistencySaver(p, cfg)
        status = saver.get_status()
        assert status["path"] == "memory://status_test3/state"
        assert status["save_interval_seconds"] == 120
        assert status["events_until_save"] == 500
        assert status["auto_load"] is True


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


class TestPersistencySaverConcurrency:
    def test_ingest_blocks_while_saver_lock_held(self):
        """ingest_event must serialize on the saver's lock so save/load can't
        race with a concurrent ingest."""
        p = EventPersistency(event_data_class=EventDataFrame)
        saver = PersistencySaver(p, PersistencySaverConfig(path="memory://concurrency/state"))
        done = threading.Event()

        def worker():
            p.ingest_event(event_id="E1", event_template="T", variables=["x"], named_variables={})
            done.set()

        with saver.locked():
            t = threading.Thread(target=worker)
            t.start()
            time.sleep(0.1)  # ample time for an unguarded ingest to complete
            assert not done.is_set(), "ingest_event ran while the saver lock was held"
            assert "E1" not in p.get_events_seen()
        t.join(timeout=1.0)
        assert done.is_set()
        assert "E1" in p.get_events_seen()

    def test_ingest_not_blocked_by_save_write(self, monkeypatch):
        """The file write must run OUTSIDE the lock: a blocked save write must
        not block a concurrent ingest_event (only serialization is guarded)."""
        import detectmatelibrary.utils.persistency.persistency_saver as ps

        p = EventPersistency(event_data_class=EventDataFrame)
        saver = PersistencySaver(p, PersistencySaverConfig(path="memory://write_block/state"))

        write_started = threading.Event()
        release_write = threading.Event()
        real_write = ps._write

        def blocking_write(fs, root, files):
            write_started.set()
            release_write.wait(timeout=2.0)
            real_write(fs, root, files)

        monkeypatch.setattr(ps, "_write", blocking_write)

        saver_thread = threading.Thread(target=saver.save)
        saver_thread.start()
        assert write_started.wait(timeout=1.0), "save write never started"

        # Write is in progress with the lock released — ingest must proceed.
        ingested = threading.Event()

        def worker():
            p.ingest_event(event_id="E2", event_template="T", variables=["y"], named_variables={})
            ingested.set()

        t = threading.Thread(target=worker)
        t.start()
        assert ingested.wait(timeout=1.0), "ingest_event blocked while save write was in progress"

        release_write.set()
        saver_thread.join(timeout=2.0)
        t.join(timeout=1.0)
        assert "E2" in p.get_events_seen()


class TestStandaloneSaveLoad:
    def test_save_creates_metadata(self):
        p = _make_persistency_with_data()
        standalone_save(p, "memory://standalone_save1/state")
        fs = fsspec.filesystem("memory")
        assert fs.exists("standalone_save1/state/metadata.json")

    def test_save_creates_event_files(self):
        p = _make_persistency_with_data()
        standalone_save(p, "memory://standalone_save2/state")
        fs = fsspec.filesystem("memory")
        assert fs.exists("standalone_save2/state/events/E1.parquet")
        assert fs.exists("standalone_save2/state/events/E2.parquet")

    def test_save_does_not_reset_events_since_save(self):
        # Module-level save() (used by export_state) is a plain snapshot and
        # must NOT touch the save counter — only PersistencySaver.save() does.
        p = _make_persistency_with_data()
        assert p._events_since_save == 3
        standalone_save(p, "memory://standalone_save3/state")
        assert p._events_since_save == 3

    def test_load_restores_events_seen(self):
        p = _make_persistency_with_data()
        standalone_save(p, "memory://standalone_load1/state")
        p2 = EventPersistency(event_data_class=EventDataFrame)
        standalone_load(p2, "memory://standalone_load1/state")
        assert "E1" in p2.get_events_seen()
        assert "E2" in p2.get_events_seen()

    def test_load_restores_event_data(self):
        p = _make_persistency_with_data()
        standalone_save(p, "memory://standalone_load2/state")
        p2 = EventPersistency(event_data_class=EventDataFrame)
        standalone_load(p2, "memory://standalone_load2/state")
        assert len(p2.get_event_data("E1")) == 2

    def test_load_restores_event_data_class(self):
        p = _make_persistency_with_data()
        standalone_save(p, "memory://standalone_load3/state")
        p2 = EventPersistency(event_data_class=EventStabilityTracker)
        standalone_load(p2, "memory://standalone_load3/state")
        assert p2.event_data_class is EventDataFrame

    def test_load_raises_when_missing(self):
        p = EventPersistency(event_data_class=EventDataFrame)
        with pytest.raises(PersistencyLoadError):
            standalone_load(p, "memory://nonexistent_standalone/state")

    def test_exported_from_package(self):
        from detectmatelibrary.utils import persistency
        assert callable(persistency.save)
        assert callable(persistency.load)

    def test_save_returns_bytes_when_no_path(self):
        p = _make_persistency_with_data()
        result = standalone_save(p)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_save_bytes_is_zip(self):
        import zipfile
        import io
        p = _make_persistency_with_data()
        data = standalone_save(p)
        assert zipfile.is_zipfile(io.BytesIO(data))

    def test_save_path_returns_none(self):
        p = _make_persistency_with_data()
        result = standalone_save(p, "memory://save_returns_none/state")
        assert result is None

    def test_load_from_bytes_restores_events_seen(self):
        p = _make_persistency_with_data()
        data = standalone_save(p)
        p2 = EventPersistency(event_data_class=EventDataFrame)
        standalone_load(p2, data)
        assert "E1" in p2.get_events_seen()
        assert "E2" in p2.get_events_seen()

    def test_load_from_bytes_restores_event_data(self):
        p = _make_persistency_with_data()
        data = standalone_save(p)
        p2 = EventPersistency(event_data_class=EventDataFrame)
        standalone_load(p2, data)
        assert len(p2.get_event_data("E1")) == 2

    def test_bytes_roundtrip_restores_event_data_class(self):
        p = _make_persistency_with_data()
        data = standalone_save(p)
        p2 = EventPersistency(event_data_class=EventStabilityTracker)
        standalone_load(p2, data)
        assert p2.event_data_class is EventDataFrame


class TestPersistencySaverThreadSafety:
    def test_load_with_running_timer_does_not_raise(self):
        p = _make_persistency_with_data()
        path = "memory://threadsafe_test/state"
        # Save initial state
        PersistencySaver(p, PersistencySaverConfig(path=path)).save()
        # Start a saver with a fast timer
        saver = PersistencySaver(p, PersistencySaverConfig(path=path, save_interval_seconds=0))
        saver.start()
        time.sleep(0.05)
        # Load into a second persistency while first saver's timer is firing
        p2 = EventPersistency(event_data_class=EventDataFrame)
        PersistencySaver(p2, PersistencySaverConfig(path=path)).load()
        saver.stop()
        assert "E1" in p2.get_events_seen()
