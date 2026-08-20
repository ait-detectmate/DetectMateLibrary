import logging
import threading

import fsspec
import numpy as np
import pytest

from detectmatelibrary import schemas
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector, ECVCDetectorConfig
from detectmatelibrary.detectors.scvs_detector import SCVSDetector, SCVSDetectorConfig
from detectmatelibrary.utils.sequence_encoding import decode_count_vec, encode_count_vec
from detectmatelibrary.detectors.new_value_detector import NewValueDetector, NewValueDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import (
    NewValueComboDetector,
    NewValueComboDetectorConfig,
)
from detectmatelibrary.detectors.new_event_detector import NewEventDetector, NewEventDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetector
from detectmatelibrary.utils.persistency.component_interfaces import PersistConfig
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

    def test_export_does_not_reset_events_since_save(self):
        # export_state is a snapshot, not a persistency save: it must not reset
        # the counter that governs the background saver's cadence.
        det = NewValueDetector(name="ExportNoReset", config=NewValueDetectorConfig(auto_config=False))
        det.persistency.ingest_event(event_id=1, event_template="login <*>", named_variables={"user": "a"})
        det.persistency.ingest_event(event_id=1, event_template="login <*>", named_variables={"user": "b"})
        assert det.persistency._events_since_save == 2
        det.export_state("memory://export_noreset/state")
        assert det.persistency._events_since_save == 2

    def test_export_state_with_running_saver_does_not_raise(self):
        # export must acquire the saver lock: a concurrent ingest + background
        # timer save would otherwise race the state snapshot.
        det = NewValueDetector(
            name="ExportSaverConcurrent",
            config=NewValueDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path="memory://export_saver_dst/state", interval_seconds=0),
            ),
        )
        stop = threading.Event()

        def ingest_loop():
            i = 0
            while not stop.is_set():
                det.persistency.ingest_event(
                    event_id=i % 5, event_template="e <*>", named_variables={"n": str(i)}
                )
                i += 1

        t = threading.Thread(target=ingest_loop)
        t.start()
        try:
            for _ in range(20):
                data = det.export_state()  # concurrent with timer save + ingest
                assert isinstance(data, bytes) and len(data) > 0
        finally:
            stop.set()
            t.join(timeout=2.0)
            det.saver.stop()


# Count-vector detectors (SCVS / ECVC) ######################################

WINDOW_SIZE = 4
# Distinct count vectors over EventIDs 0/1/4, each WINDOW_SIZE events long.
TRAIN_WINDOWS = [[0, 1, 4, 0], [1, 1, 0, 0], [4, 0, 1, 1], [0, 0, 4, 4]]
UNSEEN_WINDOW = [4, 4, 4, 4]


def _window(event_ids):
    return [schemas.ParserSchema({"EventID": i}) for i in event_ids]


class TestCountVecCodec:
    def test_round_trip(self):
        assert decode_count_vec(encode_count_vec(10, (2, 1, 0, 0, 1))) == (10, (2, 1, 0, 0, 1))

    def test_window_size_distinguishes_identical_vectors(self):
        # The same count vector learned at another window size must not match.
        assert encode_count_vec(4, (1, 1)) != encode_count_vec(8, (1, 1))


class TestSCVSDetectorPersist:
    def test_no_saver_by_default(self):
        det = SCVSDetector()
        assert det.saver is None

    def test_saver_created_when_persist_configured(self):
        det = SCVSDetector(
            name="SCVS1",
            config=SCVSDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path="memory://scvs_saver/state"),
            ),
        )
        assert det.saver is not None
        det.saver.stop()

    def test_save_and_reload(self):
        base_path = "memory://scvs_reload/state"
        det_name = "SCVS_Reload"

        det1 = SCVSDetector(
            name=det_name,
            config=SCVSDetectorConfig(
                auto_config=False,
                window_size=WINDOW_SIZE,
                persist=PersistConfig(path=base_path),
            ),
        )
        for window in TRAIN_WINDOWS:
            det1.train(_window(window))
        assert isinstance(det1.saver, PersistencySaver)
        det1.saver.save()
        det1.saver.stop()

        det2 = SCVSDetector(
            name=det_name,
            config=SCVSDetectorConfig(
                auto_config=False,
                window_size=WINDOW_SIZE,
                persist=PersistConfig(path=base_path, auto_load=True),
            ),
        )
        assert det2.get_known_count_vecs() == det1.get_known_count_vecs()
        # A restored detector detects without retraining.
        assert det2.detect(_window(TRAIN_WINDOWS[0]), schemas.DetectorSchema()) is False
        assert det2.detect(_window(UNSEEN_WINDOW), schemas.DetectorSchema()) is True
        det2.saver.stop()

    def test_import_state_warns_on_window_size_mismatch(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        det1 = SCVSDetector(
            name="SCVS_WSSrc",
            config=SCVSDetectorConfig(auto_config=False, window_size=WINDOW_SIZE),
        )
        for window in TRAIN_WINDOWS:
            det1.train(_window(window))
        state = det1.export_state()

        det2 = SCVSDetector(
            name="SCVS_WSDst",
            config=SCVSDetectorConfig(auto_config=False, window_size=WINDOW_SIZE + 2),
        )
        with caplog.at_level(logging.WARNING):
            det2.import_state(state)
        assert any("window_size" in r.message for r in caplog.records)


class TestECVCDetectorPersist:
    def test_no_saver_by_default(self):
        det = ECVCDetector()
        assert det.saver is None

    def test_saver_created_when_persist_configured(self):
        det = ECVCDetector(
            name="ECVC1",
            config=ECVCDetectorConfig(
                auto_config=False,
                persist=PersistConfig(path="memory://ecvc_saver/state"),
            ),
        )
        assert det.saver is not None
        det.saver.stop()

    def test_save_and_reload_rebuilds_model(self):
        """A reloaded ECVC must derive the same matrix and threshold.

        post_train() splits train from validation by iteration order
        over the learned vectors, so a restored model only equals a
        freshly trained one because _derive() sorts them first.
        """
        base_path = "memory://ecvc_reload/state"
        det_name = "ECVC_Reload"
        config_args = dict(
            auto_config=False,
            window_size=WINDOW_SIZE,
            validation_per=0.5,
            seed=0,
            threshold_method="mean",
        )

        det1 = ECVCDetector(
            name=det_name,
            config=ECVCDetectorConfig(
                persist=PersistConfig(path=base_path), **config_args
            ),
        )
        for window in TRAIN_WINDOWS:
            det1.train(_window(window))
        det1.post_train()
        assert det1.count_vecs is not None
        assert isinstance(det1.saver, PersistencySaver)
        det1.saver.save()
        det1.saver.stop()

        det2 = ECVCDetector(
            name=det_name,
            config=ECVCDetectorConfig(
                persist=PersistConfig(path=base_path, auto_load=True), **config_args
            ),
        )
        assert det2.count_vecs is not None
        assert np.array_equal(det2.count_vecs, det1.count_vecs)
        assert det2.threshold == det1.threshold
        det2.saver.stop()

    def test_import_state_rebuilds_model(self):
        config_args = dict(
            auto_config=False, window_size=WINDOW_SIZE, validation_per=0.5, seed=0
        )
        det1 = ECVCDetector(name="ECVC_ImpSrc", config=ECVCDetectorConfig(**config_args))
        for window in TRAIN_WINDOWS:
            det1.train(_window(window))
        det1.post_train()
        state = det1.export_state()

        det2 = ECVCDetector(name="ECVC_ImpDst", config=ECVCDetectorConfig(**config_args))
        assert det2.count_vecs is None  # nothing learned yet
        det2.import_state(state)
        assert det2.count_vecs is not None
        assert np.array_equal(det2.count_vecs, det1.count_vecs)

    def test_untrained_detector_stays_silent(self):
        det = ECVCDetector(name="ECVC_Empty", config=ECVCDetectorConfig(auto_config=False))
        assert det.detect(_window(UNSEEN_WINDOW), schemas.DetectorSchema()) is False
