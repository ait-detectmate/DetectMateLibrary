import fsspec

from detectmatelibrary.detectors.new_value_detector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import (
    NewValueComboDetector,
    NewValueComboDetectorConfig,
)
from detectmatelibrary.detectors.new_event_detector import NewEventDetector, NewEventDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetector
from detectmatelibrary.common.detector import PersistConfig
from detectmatelibrary.utils.persistency.persistency_saver import PersistencySaver


class TestNewValueDetectorPersist:
    def test_no_saver_by_default(self):
        det = NewValueDetector()
        assert det.saver is None

    def test_saver_created_when_persist_configured(self):
        config = NewValueDetectorConfig(
            auto_config=True,
            persist=PersistConfig(path="memory://nvd_saver/state"),
        )
        det = NewValueDetector(name="NVD1", config=config)
        assert det.saver is not None
        det.saver.stop()

    def test_save_and_reload(self):
        base_path = "memory://nvd_reload/state"
        det_name = "NVD_Reload"

        det1 = NewValueDetector(
            name=det_name,
            config=NewValueDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path=base_path),
            ),
        )
        det1.persistency.ingest_event(
            event_id=1,
            event_template="login <*>",
            named_variables={"user": "alice"},
        )
        assert det1.saver is not None
        assert isinstance(det1.saver, PersistencySaver)
        det1.saver.save()
        det1.saver.stop()

        det2 = NewValueDetector(
            name=det_name,
            config=NewValueDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert 1 in det2.persistency.get_events_seen()
        assert det2.saver is not None
        det2.saver.stop()

    def test_set_configuration_preserves_persist_config(self):
        """Persist field must survive an auto-config set_configuration()
        rebuild."""
        config = NewValueDetectorConfig(
            auto_config=True,
            persist=PersistConfig(path="memory://set_config_preserve/state"),
        )
        det = NewValueDetector(name="SetConfigTest", config=config)
        assert det.config.persist is not None  # sanity: persist is set before
        det.set_configuration()
        assert det.config.persist is not None  # must survive config rebuild
        assert det.config.persist.path == "memory://set_config_preserve/state"
        assert det.saver is not None
        det.saver.stop()


class TestNewValueComboDetectorPersist:
    def test_no_saver_by_default(self):
        det = NewValueComboDetector()
        assert det.saver is None

    def test_saver_created_when_persist_configured(self):
        config = NewValueComboDetectorConfig(
            auto_config=True,
            persist=PersistConfig(path="memory://nvcd_saver/state"),
        )
        det = NewValueComboDetector(name="NVCD1", config=config)
        assert det.saver is not None
        det.saver.stop()

    def test_save_and_reload(self):
        base_path = "memory://nvcd_reload/state"
        det_name = "NVCD_Reload"

        det1 = NewValueComboDetector(
            name=det_name,
            config=NewValueComboDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path=base_path),
            ),
        )
        det1.persistency.ingest_event(
            event_id=1,
            event_template="login <*>",
            named_variables={"user": "alice"},
        )
        assert det1.saver is not None
        assert isinstance(det1.saver, PersistencySaver)
        det1.saver.save()
        det1.saver.stop()

        det2 = NewValueComboDetector(
            name=det_name,
            config=NewValueComboDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert 1 in det2.persistency.get_events_seen()
        assert det2.saver is not None
        det2.saver.stop()


class TestNewEventDetectorPersist:
    def test_no_saver_by_default(self):
        det = NewEventDetector()
        assert det.saver is None

    def test_saver_created_when_persist_configured(self):
        config = NewEventDetectorConfig(
            auto_config=True,
            persist=PersistConfig(path="memory://ned_saver/state"),
        )
        det = NewEventDetector(name="NED1", config=config)
        assert det.saver is not None
        det.saver.stop()


class TestDetectorExportImportState:
    def test_export_state_creates_metadata(self):
        det = NewValueDetector(
            name="ExportTest",
            config=NewValueDetectorConfig(auto_config=False),
        )
        det.persistency.ingest_event(
            event_id=1, event_template="login <*>", named_variables={"user": "alice"}
        )
        det.export_state("memory://export_state_test/state")
        assert fsspec.filesystem("memory").exists("export_state_test/state/metadata.json")

    def test_export_state_creates_event_files(self):
        det = NewValueDetector(
            name="ExportFiles",
            config=NewValueDetectorConfig(auto_config=False),
        )
        det.persistency.ingest_event(
            event_id=2, event_template="logout <*>", named_variables={"user": "bob"}
        )
        det.export_state("memory://export_files_test/state")
        # NewValueDetector uses EventStabilityTracker → msgpack extension
        assert fsspec.filesystem("memory").exists("export_files_test/state/events/2.msgpack")

    def test_import_state_restores_events_seen(self):
        det1 = NewValueDetector(name="ImportSrc", config=NewValueDetectorConfig(auto_config=False))
        det1.persistency.ingest_event(
            event_id=1, event_template="login <*>", named_variables={"user": "alice"}
        )
        det1.export_state("memory://import_state_test/state")

        det2 = NewValueDetector(name="ImportDst", config=NewValueDetectorConfig(auto_config=False))
        det2.import_state("memory://import_state_test/state")
        assert 1 in det2.persistency.get_events_seen()

    def test_import_state_with_running_saver_does_not_raise(self):
        det1 = NewValueDetector(name="ImportSaverSrc", config=NewValueDetectorConfig(auto_config=False))
        det1.persistency.ingest_event(
            event_id=3, event_template="connect <*>", named_variables={"host": "srv1"}
        )
        det1.export_state("memory://import_saver_test/state")

        det2 = NewValueDetector(
            name="ImportSaverDst",
            config=NewValueDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path="memory://import_saver_dst/state"),
            ),
        )
        det2.import_state("memory://import_saver_test/state")
        det2.saver.stop()
        assert 3 in det2.persistency.get_events_seen()

    def test_export_returns_none_without_persistency(self):
        det = RuleDetector()
        assert det.export_state("memory://any/path") is None

    def test_import_noop_without_persistency(self):
        det = RuleDetector()
        # No persistency configured: import is a silent no-op, not an error.
        det.import_state("memory://any/path")

    def test_export_state_returns_bytes_when_no_path(self):
        det = NewValueDetector(name="ExportBytes", config=NewValueDetectorConfig(auto_config=False))
        det.persistency.ingest_event(
            event_id=1, event_template="login <*>", named_variables={"user": "alice"}
        )
        result = det.export_state()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_state_path_returns_none(self):
        det = NewValueDetector(name="ExportNone", config=NewValueDetectorConfig(auto_config=False))
        det.persistency.ingest_event(
            event_id=1, event_template="login <*>", named_variables={"user": "alice"}
        )
        result = det.export_state("memory://export_none_test/state")
        assert result is None

    def test_import_state_accepts_bytes(self):
        det1 = NewValueDetector(name="BytesSrc", config=NewValueDetectorConfig(auto_config=False))
        det1.persistency.ingest_event(
            event_id=5, event_template="login <*>", named_variables={"user": "alice"}
        )
        data = det1.export_state()

        det2 = NewValueDetector(name="BytesDst", config=NewValueDetectorConfig(auto_config=False))
        det2.import_state(data)
        assert 5 in det2.persistency.get_events_seen()
