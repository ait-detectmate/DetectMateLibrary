from detectmatelibrary.utils.persistency.exceptions import PersistencyLoadError
from detectmatelibrary.utils.persistency.event_data_structures.base import EventDataStructure


def test_persistency_load_error_is_exception():
    err = PersistencyLoadError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_event_data_structure_has_dump_load():
    assert hasattr(EventDataStructure, "dump")
    assert hasattr(EventDataStructure, "load")
