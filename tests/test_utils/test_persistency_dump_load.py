import pytest
from dataclasses import dataclass

from detectmatelibrary.utils.persistency.exceptions import PersistencyLoadError
from detectmatelibrary.utils.persistency.event_data_structures.base import EventDataStructure


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
