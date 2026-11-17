"""Tests for detectmatelibrary.base_detectors._persist."""
import fsspec
import pytest
from pydantic import ValidationError

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.base_detectors import PersistConfig, TrackerDetectorConfig
from detectmatelibrary.base_detectors._persist import start_saver
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency


class TestPersistConfig:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("STATE_DIRECTORY", raising=False)
        cfg = PersistConfig()
        assert cfg.path == "./state"
        assert cfg.interval_seconds == 300
        assert cfg.events_until_save is None
        assert cfg.auto_load is False
        assert cfg.storage_options == {}

    def test_custom_values(self):
        cfg = PersistConfig(path="./my-path", interval_seconds=60, auto_load=True)
        assert cfg.path == "./my-path"
        assert cfg.interval_seconds == 60
        assert cfg.auto_load is True

    def test_events_until_save_accepts_int(self):
        cfg = PersistConfig(events_until_save=500)
        assert cfg.events_until_save == 500

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            PersistConfig(unknown_field="value")  # type: ignore


class TestPersistConfigStateDirectoryDefault:
    def test_uses_state_directory_env_when_set(self, monkeypatch):
        monkeypatch.setenv("STATE_DIRECTORY", "/var/lib/detectmate")
        assert PersistConfig().path == "/var/lib/detectmate"

    def test_takes_first_path_when_state_directory_is_colon_list(self, monkeypatch):
        # systemd sets STATE_DIRECTORY colon-separated for multiple StateDirectory= entries
        monkeypatch.setenv("STATE_DIRECTORY", "/var/lib/a:/var/lib/b")
        assert PersistConfig().path == "/var/lib/a"

    def test_falls_back_to_state_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("STATE_DIRECTORY", raising=False)
        assert PersistConfig().path == "./state"

    def test_explicit_path_overrides_state_directory_env(self, monkeypatch):
        monkeypatch.setenv("STATE_DIRECTORY", "/var/lib/detectmate")
        assert PersistConfig(path="s3://bucket/state").path == "s3://bucket/state"


class TestTrackerDetectorConfigPersistField:
    def test_persist_is_none_by_default(self):
        cfg = TrackerDetectorConfig()
        assert cfg.persist is None

    def test_persist_accepts_persist_config(self):
        cfg = TrackerDetectorConfig(persist=PersistConfig(path="./custom"))
        assert cfg.persist is not None
        assert cfg.persist.path == "./custom"

    def test_persist_accepts_none_explicitly(self):
        cfg = TrackerDetectorConfig(persist=None)
        assert cfg.persist is None

    def test_core_detector_config_has_no_persist(self):
        with pytest.raises(ValidationError, match="persist"):
            CoreDetectorConfig(persist=None)


class TestStartSaver:
    def test_none_when_persist_is_none(self):
        assert start_saver("MyDetector", None, EventPersistency()) is None

    def test_creates_saver_when_persist_configured(self):
        persist = PersistConfig(path="memory://regpersist_create/state")
        saver = start_saver("MyDetector", persist, EventPersistency())
        assert saver is not None
        saver.stop()

    def test_saver_path_includes_detector_name(self):
        persist = PersistConfig(path="memory://regpersist_path/state")
        saver = start_saver("MyDetector", persist, EventPersistency())
        assert saver is not None
        saver.stop()  # stop() calls save() as final save
        fs = fsspec.filesystem("memory")
        assert fs.exists("regpersist_path/state/MyDetector/metadata.json")
