"""Tests for detectmatelibrary.utils.persistency.basic_persistency."""
from detectmatelibrary.utils.persistency.basic_persistency import PersistencyStruct, get_all_variables
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
