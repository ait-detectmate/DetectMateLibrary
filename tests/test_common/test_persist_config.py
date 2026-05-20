import warnings

import fsspec
import pytest
from pydantic import ValidationError

from detectmatelibrary.common._config._compile import MissingParamsWarning
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig, PersistConfig
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.utils.persistency.event_data_structures.trackers import EventStabilityTracker
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency


class TestPersistConfig:
    def test_defaults(self):
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


class TestPersistConfigSerialization:
    def test_to_dict_places_persist_at_top_level(self):
        config = NewValueDetectorConfig(
            auto_config=True,
            persist=PersistConfig(path="./my-state", interval_seconds=60),
        )
        result = config.to_dict("MyDet")
        inner = result["detectors"]["MyDet"]
        assert "persist" in inner
        assert inner["persist"]["path"] == "./my-state"
        assert inner["persist"]["interval_seconds"] == 60
        assert "persist" not in inner.get("params", {})

    def test_to_dict_omits_persist_when_none(self):
        config = NewValueDetectorConfig(auto_config=True)
        result = config.to_dict("MyDet")
        inner = result["detectors"]["MyDet"]
        assert "persist" not in inner

    def test_from_dict_loads_persist_block(self):
        config_dict = {
            "detectors": {
                "MyDet": {
                    "method_type": "new_value_detector",
                    "auto_config": True,
                    "persist": {"path": "./my-state", "interval_seconds": 60},
                }
            }
        }
        config = NewValueDetectorConfig.from_dict(config_dict, "MyDet")
        assert config.persist is not None
        assert config.persist.path == "./my-state"
        assert config.persist.interval_seconds == 60

    def test_roundtrip_yaml_to_pydantic_to_yaml(self):
        config_dict = {
            "detectors": {
                "MyDet": {
                    "method_type": "new_value_detector",
                    "auto_config": True,
                    "persist": {"path": "./my-state"},
                }
            }
        }
        config = NewValueDetectorConfig.from_dict(config_dict, "MyDet")
        result = config.to_dict("MyDet")
        assert result["detectors"]["MyDet"]["persist"]["path"] == "./my-state"

    def test_no_missing_params_warning_with_persist_only(self):
        config_dict = {
            "detectors": {
                "MyDet": {
                    "method_type": "new_value_detector",
                    "auto_config": False,
                    "persist": {"path": "./state"},
                }
            }
        }
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NewValueDetectorConfig.from_dict(config_dict, "MyDet")
        missing_params_warnings = [x for x in w if issubclass(x.category, MissingParamsWarning)]
        assert len(missing_params_warnings) == 0
