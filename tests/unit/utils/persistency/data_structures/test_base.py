"""Tests for detectmatelibrary.utils.persistency.data_structures.base."""
import pytest
from dataclasses import dataclass
from detectmatelibrary.utils.persistency.data_structures.base import (
    EventDataset,
)


def test_event_data_structure_has_dump_load():
    assert hasattr(EventDataset, "dump")
    assert hasattr(EventDataset, "load")


def test_subclass_without_dump_load_cannot_be_instantiated():
    @dataclass
    class _Incomplete(EventDataset):
        def add_data(self, data_object): pass
        def get_data(self): pass
        def get_variables(self): pass
        def to_data(self, raw_data): pass
        # intentionally missing dump() and load()

    with pytest.raises(TypeError):
        _Incomplete()
