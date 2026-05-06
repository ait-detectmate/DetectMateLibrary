import fsspec
import pytest
from pydantic import ValidationError

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig, PersistConfig
from detectmatelibrary.utils.persistency.event_data_structures.trackers import EventStabilityTracker
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency


class TestPersistConfig:
    def test_defaults(self):
        cfg = PersistConfig()
        assert cfg.path == "./state"
        assert cfg.interval_seconds == 300
        assert cfg.dirty_threshold is None
        assert cfg.auto_load is False
        assert cfg.storage_options == {}

    def test_custom_values(self):
        cfg = PersistConfig(path="./my-path", interval_seconds=60, auto_load=True)
        assert cfg.path == "./my-path"
        assert cfg.interval_seconds == 60
        assert cfg.auto_load is True

    def test_dirty_threshold_accepts_int(self):
        cfg = PersistConfig(dirty_threshold=500)
        assert cfg.dirty_threshold == 500

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            PersistConfig(unknown_field="value")  # type: ignore


class TestCoreDetectorConfigPersistField:
    def test_persist_is_none_by_default(self):
        cfg = CoreDetectorConfig()
        assert cfg.persist is None

    def test_persist_accepts_persist_config(self):
        cfg = CoreDetectorConfig(persist=PersistConfig(path="./custom"))
        assert cfg.persist is not None
        assert cfg.persist.path == "./custom"

    def test_persist_accepts_none_explicitly(self):
        cfg = CoreDetectorConfig(persist=None)
        assert cfg.persist is None


class TestRegisterPersistency:
    def test_noop_when_persist_is_none(self):
        det = CoreDetector()
        p = EventPersistency(event_data_class=EventStabilityTracker)
        det._register_persistency(p)
        assert det.saver is None

    def test_creates_saver_when_persist_configured(self):
        config = CoreDetectorConfig(
            persist=PersistConfig(path="memory://regpersist_create/state")
        )
        det = CoreDetector(config=config)
        p = EventPersistency(event_data_class=EventStabilityTracker)
        det._register_persistency(p)
        assert det.saver is not None
        det.saver.stop()

    def test_saver_path_includes_detector_name(self):
        config = CoreDetectorConfig(
            persist=PersistConfig(path="memory://regpersist_path/state")
        )
        det = CoreDetector(name="MyDetector", config=config)
        p = EventPersistency(event_data_class=EventStabilityTracker)
        det._register_persistency(p)
        assert det.saver is not None
        det.saver.stop()  # stop() calls save() as final save
        fs = fsspec.filesystem("memory")
        assert fs.exists("regpersist_path/state/MyDetector/metadata.json")
