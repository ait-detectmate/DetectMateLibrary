import pytest
import pandas as pd
import polars as pl
from dataclasses import dataclass

from detectmatelibrary.utils.persistency.exceptions import PersistencyLoadError
from detectmatelibrary.utils.persistency.event_data_structures.base import (
    EventDataStructure,
)
from detectmatelibrary.utils.persistency.event_data_structures.dataframes.event_dataframe import (
    EventDataFrame,
)
from detectmatelibrary.utils.persistency.event_data_structures.dataframes.chunked_event_dataframe import (
    ChunkedEventDataFrame,
)
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
    EventStabilityTracker,
)


def test_persistency_load_error_is_exception():
    err = PersistencyLoadError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_event_data_structure_has_dump_load():
    assert hasattr(EventDataStructure, "dump")
    assert hasattr(EventDataStructure, "load")


def test_subclass_without_dump_load_cannot_be_instantiated():
    @dataclass
    class _Incomplete(EventDataStructure):
        def add_data(self, data_object): pass
        def get_data(self): pass
        def get_variables(self): pass
        def to_data(self, raw_data): pass
        # intentionally missing dump() and load()

    with pytest.raises(TypeError):
        _Incomplete()


class TestSingleStabilityTrackerState:
    def _make_tracker(self) -> SingleStabilityTracker:
        t = SingleStabilityTracker(min_samples=3)
        for v in ["a", "b", "a", "c", "a"]:
            t.add_value(v)
        return t

    def test_round_trip_preserves_change_series(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert list(t2.change_series) == list(t.change_series)

    def test_round_trip_preserves_unique_set(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert t2.unique_set == t.unique_set

    def test_round_trip_preserves_min_samples(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert t2.min_samples == 3

    def test_round_trip_preserves_classification(self):
        t = self._make_tracker()
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert t2.classify().type == t.classify().type

    def test_state_includes_type_and_module(self):
        t = SingleStabilityTracker()
        state = t.to_state()
        assert state["type"] == "SingleStabilityTracker"
        assert "module" in state

    def test_empty_tracker_round_trip(self):
        t = SingleStabilityTracker(min_samples=5)
        state = t.to_state()
        t2 = SingleStabilityTracker.from_state(state)
        assert len(t2.change_series) == 0
        assert len(t2.unique_set) == 0


class TestEventTrackerDumpLoad:
    def _make_tracker(self) -> EventStabilityTracker:
        t = EventStabilityTracker()
        for i in range(10):
            t.add_data({"var_0": f"value_{i % 3}", "var_1": str(i)})
        return t

    def test_dump_returns_bytes(self):
        t = self._make_tracker()
        assert isinstance(t.dump(), bytes)

    def test_round_trip_restores_tracker_keys(self):
        t = self._make_tracker()
        t2 = EventStabilityTracker.load(t.dump())
        assert set(t2.get_data().keys()) == set(t.get_data().keys())

    def test_round_trip_preserves_change_series(self):
        t = self._make_tracker()
        t2 = EventStabilityTracker.load(t.dump())
        for key in t.get_data():
            original = list(t.get_data()[key].change_series)
            restored = list(t2.get_data()[key].change_series)
            assert restored == original

    def test_round_trip_preserves_unique_set(self):
        t = self._make_tracker()
        t2 = EventStabilityTracker.load(t.dump())
        for key in t.get_data():
            assert t2.get_data()[key].unique_set == t.get_data()[key].unique_set

    def test_empty_tracker_round_trip(self):
        t = EventStabilityTracker()
        t2 = EventStabilityTracker.load(t.dump())
        assert t2.get_data() == {}


class TestEventDataFrameDumpLoad:
    def _make_edf(self) -> EventDataFrame:
        edf = EventDataFrame()
        edf.add_data(edf.to_data({"user": "alice", "ip": "192.168.1.1"}))
        edf.add_data(edf.to_data({"user": "bob",   "ip": "192.168.1.2"}))
        return edf

    def test_dump_returns_bytes(self):
        assert isinstance(self._make_edf().dump(), bytes)

    def test_round_trip_preserves_rows(self):
        edf = self._make_edf()
        edf2 = EventDataFrame.load(edf.dump())
        assert len(edf2.get_data()) == 2

    def test_round_trip_preserves_columns(self):
        edf = self._make_edf()
        edf2 = EventDataFrame.load(edf.dump())
        assert list(edf2.get_data().columns) == ["user", "ip"]

    def test_round_trip_preserves_values(self):
        edf = self._make_edf()
        edf2 = EventDataFrame.load(edf.dump())
        assert edf2.get_data()["user"].tolist() == ["alice", "bob"]

    def test_empty_dataframe_round_trip(self):
        edf = EventDataFrame()
        edf2 = EventDataFrame.load(edf.dump())
        assert isinstance(edf2.get_data(), pd.DataFrame)
        assert len(edf2.get_data()) == 0


class TestChunkedEventDataFrameDumpLoad:
    def _make_cedf(self) -> ChunkedEventDataFrame:
        cedf = ChunkedEventDataFrame(max_rows=100, compact_every=1000)
        for i in range(5):
            cedf.add_data(cedf.to_data({"user": [f"user_{i}"], "val": [i]}))
        return cedf

    def test_dump_returns_bytes(self):
        assert isinstance(self._make_cedf().dump(), bytes)

    def test_round_trip_preserves_rows(self):
        cedf = self._make_cedf()
        cedf2 = ChunkedEventDataFrame.load(cedf.dump())
        assert len(cedf2.get_data()) == 5

    def test_round_trip_preserves_columns(self):
        cedf = self._make_cedf()
        cedf2 = ChunkedEventDataFrame.load(cedf.dump())
        assert set(cedf2.get_data().columns) == {"user", "val"}

    def test_round_trip_restores_config(self):
        cedf = ChunkedEventDataFrame(max_rows=42, compact_every=7)
        cedf.add_data(cedf.to_data({"x": [1]}))
        cedf2 = ChunkedEventDataFrame.load(cedf.dump())
        assert cedf2.max_rows == 42
        assert cedf2.compact_every == 7

    def test_empty_round_trip(self):
        cedf = ChunkedEventDataFrame()
        cedf2 = ChunkedEventDataFrame.load(cedf.dump())
        assert isinstance(cedf2.get_data(), pl.DataFrame)
        assert len(cedf2.get_data()) == 0
