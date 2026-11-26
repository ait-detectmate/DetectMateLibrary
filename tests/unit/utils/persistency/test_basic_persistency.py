"""Tests for detectmatelibrary.utils.persistency.basic_persistency."""
from detectmatelibrary.utils.persistency.basic_persistency import PersistencyStruct, get_all_variables
import polars as pl
import pytest


class TestPersistencyStruct:
    def test_add_slow(self) -> None:
        pers_struct = PersistencyStruct(do_slow_pers=True)
        vars = get_all_variables(
            variables=["a", "b"],
            log_format_variables={"hi": 2},
            variable_blacklist=[]
        )

        pers_struct.update_data_structure(
            event_id="E01", variables=vars, template="as", timestamp=None
        )

        df = pers_struct.get_data()

        assert df["EventIDs"][0] == "E01"
        assert len(df) == 1
        pers_struct.slow_persistency  # no raise issue

    def test_add_slow_disable(self) -> None:
        pers_struct = PersistencyStruct(do_slow_pers=False)
        vars = get_all_variables(
            variables=["a", "b"],
            log_format_variables={"hi": 2},
            variable_blacklist=[]
        )

        pers_struct.update_data_structure(
            event_id="E01", variables=vars, template="as", timestamp=None
        )

        df = pers_struct.get_data()
        assert df.shape[0] == 0
        with pytest.raises(AttributeError):
            pers_struct.slow_persistency


class TestPersistencyStructEquality:
    def _struct(self, *values: str) -> PersistencyStruct:
        struct = PersistencyStruct(do_slow_pers=False)
        for value in values:
            variables = get_all_variables([value], {}, [])
            struct.update_data_structure(
                event_id="E01", variables=variables, template="t <*>", timestamp=None)
        return struct

    def test_equal_contents_are_equal(self):
        assert self._struct("a") == self._struct("a")

    def test_other_event_counts_or_types_are_not_equal(self):
        assert self._struct("a") != PersistencyStruct(do_slow_pers=False)
        assert self._struct("a") != "not a struct"

    @pytest.mark.xfail(strict=True, raises=AssertionError,
                       reason="B11: equality compares the trackers' as_dict(), which is always []")
    def test_different_learned_values_are_not_equal(self):
        assert self._struct("a") != self._struct("b")

    def test_overwriting_a_disabled_slow_store_warns(self):
        with pytest.warns(UserWarning, match="Slow persistency was disabled"):
            PersistencyStruct(do_slow_pers=False).overwrite_slow(pl.DataFrame())
