from detectmatelibrary.detectors.new_value_detector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import (
    NewValueComboDetector,
    NewValueComboDetectorConfig,
)
from detectmatelibrary.detectors.new_event_detector import NewEventDetector, NewEventDetectorConfig
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
