"""TrackerDetector: the one owner of EventPersistency stores."""
from pathlib import Path

import fsspec
import pytest

from detectmatelibrary import schemas
from detectmatelibrary.subcommon import (
    PersistConfig,
    StabilityAutoConfigParams,
    TrackerDetector,
    TrackerDetectorConfig,
)
from detectmatelibrary.utils.persistency.data_structures.trackers.stability import ClassificationMethods
from detectmatelibrary.utils.persistency.persistency_saver import PersistencyLoadError


def _event(event_id: int) -> schemas.ParserSchema:
    return schemas.ParserSchema({
        "parserType": "test",
        "EventID": event_id,
        "template": "test template",
        "variables": [],
        "logID": str(event_id),
        "parsedLogID": str(event_id),
        "parserID": "test_parser",
        "log": "test log message",
        "logFormatVariables": {},
    })


class _Recorder(TrackerDetector):
    """Counts `_sync_from_state` calls; trains by ingesting the EventID."""

    def __init__(
        self,
        name: str = "Recorder",
        config: TrackerDetectorConfig = TrackerDetectorConfig(),
        stability_params: StabilityAutoConfigParams = StabilityAutoConfigParams(),
    ) -> None:
        self.synced = 0  # before super().__init__: the first sync runs inside it
        super().__init__(name=name, config=config, stability_params=stability_params)

    def _sync_from_state(self) -> None:
        self.synced += 1

    def train(self, input_: schemas.ParserSchema) -> None:  # type: ignore[override]
        self._ingest(input_, {}, input_["EventID"])


class TestSyncFromState:
    def test_runs_once_at_construction(self) -> None:
        assert _Recorder().synced == 1

    def test_runs_after_import_state(self) -> None:
        source = _Recorder()
        source.train(_event(1))
        target = _Recorder()
        target.import_state(source.export_state())
        assert target.synced == 2
        assert target.persistency.get_events_seen() == {1}

    def test_does_not_run_when_import_state_fails(self) -> None:
        det = _Recorder()
        det.train(_event(1))
        with pytest.raises(PersistencyLoadError, match="metadata.json missing"):
            det.import_state("memory://tracker_persist/never_saved")
        assert det.synced == 1
        assert det.persistency.get_events_seen() == {1}

    def test_runs_on_the_detector_from_binary_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)  # the slow store writes .temp/ CSVs here
        source = _Recorder(config=TrackerDetectorConfig(allow_fed=True))
        source.train(_event(1))
        restored = source.from_binary(source.to_binary())
        assert restored.synced == 2
        assert restored.persistency.get_events_seen() == {1}

    def test_runs_on_every_component_after_aggregate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        a = _Recorder(config=TrackerDetectorConfig(allow_fed=True))
        b = _Recorder(config=TrackerDetectorConfig(allow_fed=True))
        a.train(_event(1))
        b.train(_event(2))
        a + b
        a.aggregate()
        assert (a.synced, b.synced) == (2, 2)
        assert a.persistency is b.persistency
        assert a.persistency.get_events_seen() == {1, 2}


class TestNewStore:
    _TIME = StabilityAutoConfigParams(classification=ClassificationMethods(time=True))

    def test_classified_store_uses_configured_methods(self) -> None:
        store = _Recorder(stability_params=self._TIME)._new_store({"k": 1}, classified=True)
        assert store.event_struct.data_kwargs == {
            "k": 1, "classification": self._TIME.classification.model_dump()
        }

    def test_plain_store_ignores_configured_methods(self) -> None:
        store = _Recorder(stability_params=self._TIME)._new_store({"k": 1})
        assert store.event_struct.data_kwargs == {"k": 1}

    def test_default_methods_add_nothing(self) -> None:
        store = _Recorder()._new_store(classified=True)
        assert store.event_struct.data_kwargs == {}


class TestPersist:
    def test_saver_saves_the_main_store_on_exit(self) -> None:
        config = TrackerDetectorConfig(persist=PersistConfig(path="memory://tracker_persist/state"))
        with _Recorder(config=config) as det:
            assert det.saver is not None
            assert det.saver._persistency is det.persistency
            det.train(_event(1))
        assert fsspec.filesystem("memory").exists("tracker_persist/state/Recorder/metadata.json")

    def test_no_saver_without_persist(self) -> None:
        assert _Recorder().saver is None

    def test_with_block_without_persist(self) -> None:
        with _Recorder() as det:
            det.train(_event(1))
        assert det.persistency.get_events_seen() == {1}


class TestFinalizeFederation:
    def test_removes_the_slow_table_with_allow_fed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        det = _Recorder(config=TrackerDetectorConfig(allow_fed=True))
        det.train(_event(1))
        assert (tmp_path / ".temp").exists()
        det.finalize_federation()
        assert not (tmp_path / ".temp").exists()

    def test_is_a_no_op_without_allow_fed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".temp").mkdir()
        (tmp_path / ".temp" / ".keep.csv").write_text("")
        _Recorder().finalize_federation()
        assert (tmp_path / ".temp" / ".keep.csv").exists()
