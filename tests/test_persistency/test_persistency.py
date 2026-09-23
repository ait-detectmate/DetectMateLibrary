"""Tests for the persistency module core functionality.

This module tests EventPersistency and data structure backends including
EventDataFrame (Pandas) and ChunkedEventDataFrame (Polars).
"""


from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.data_structures.trackers import (
    EventTracker,
    SingleStabilityTracker,
    EventStabilityTracker
)
from detectmatelibrary.utils.persistency.slow_persistency import SlowPersistency, Manager
from detectmatelibrary.utils.persistency.basic_persistency import PersistencyStruct, get_all_variables

import pytest
import polars as pl
import os


# Sample test data - variables is a list, not a dict
SAMPLE_EVENT_1 = {
    "event_id": "E001",
    "event_template": "User <*> logged in from <*>",
    "variables": ["alice", "192.168.1.1"],
    "named_variables": {"timestamp": "2024-01-01 10:00:00"},
}

SAMPLE_EVENT_2 = {
    "event_id": "E002",
    "event_template": "Error in module <*>: <*>",
    "variables": ["auth", "timeout"],
    "named_variables": {"timestamp": "2024-01-01 10:01:00"},
}

SAMPLE_EVENT_3 = {
    "event_id": "E001",
    "event_template": "User <*> logged in from <*>",
    "variables": ["bob", "192.168.1.2"],
    "named_variables": {"timestamp": "2024-01-01 10:02:00"},
}


class TestSlowPersisntecy:
    def test_buffer(self) -> None:
        persistency = SlowPersistency(columns=[], file_manager=Manager, buffer_size=2)
        persistency.file_manager.test_buffer = []  # Remove columns name insertion

        persistency.add(["a", 2])
        assert len(persistency.buffer) == 1
        assert len(persistency.file_manager.test_buffer) == 0

        persistency.add(["b", 1])
        assert len(persistency.buffer) == 0
        assert len(persistency.file_manager.test_buffer) == 2

        persistency.add(["c", 1])
        assert len(persistency.buffer) == 1
        assert len(persistency.file_manager.test_buffer) == 2

        persistency.push_buffer()
        assert len(persistency.buffer) == 0
        assert len(persistency.file_manager.test_buffer) == 3

    def test_csv_frame_file(self) -> None:
        persistency = SlowPersistency(columns=["char", "int"], buffer_size=2)
        persistency.add(["a", 2])
        persistency.add(["b", 2])

        assert os.path.exists(persistency.path)

        df = persistency.load()
        expected = pl.DataFrame({"char": ["a", "b"], "int": [2, 2]})
        assert df.equals(expected)

        persistency.reset()
        assert not os.path.exists(persistency.path)

    def test_transfer(self) -> None:
        persistency = SlowPersistency(columns=["char", "int"], buffer_size=2)
        persistency.add(["a", 2])
        persistency.add(["b", 2])

        df = persistency.load()

        assert len(df) == 2
        assert persistency == SlowPersistency.from_dataframe(df)


class TestPersistencyStruct:
    def test_add_slow(self) -> None:
        pers_struct = PersistencyStruct()
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


class TestEventPersistency:
    """Test suite for EventPersistency orchestrator class."""

    def test_initialization_with_tracker_backend(self):
        """Test initialization with EventVariableTrackerData backend."""
        persistency = EventPersistency(
            event_data_kwargs={"tracker_type": SingleStabilityTracker},
        )
        assert persistency is not None

    def test_ingest_multiple_events_same_id(self):
        """Test ingesting multiple events with the same ID."""
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_3)

        data = persistency.get_event_data("E001")
        assert len(data) == 3

    def test_ingest_multiple_events_different_ids(self):
        """Test ingesting events with different IDs."""
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        data1 = persistency.get_event_data("E001")
        data2 = persistency.get_event_data("E002")

        assert len(data1) == 3
        assert len(data2) == 3

    def test_get_all_events_data(self):
        """Test retrieving data for all events."""
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        all_data = persistency.get_events_data()
        assert "E001" in all_data
        assert "E002" in all_data
        assert isinstance(all_data["E001"], EventStabilityTracker)
        assert isinstance(all_data["E002"], EventStabilityTracker)

    def test_template_storage_and_retrieval(self):
        """Test template storage and retrieval."""
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        template1 = persistency.get_event_template("E001")
        template2 = persistency.get_event_template("E002")

        assert template1 == "User <*> logged in from <*>"
        assert template2 == "Error in module <*>: <*>"

    def test_get_all_templates(self):
        """Test retrieving all templates."""
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        templates = persistency.get_event_templates()
        assert len(templates) == 2
        assert templates["E001"] == "User <*> logged in from <*>"
        assert templates["E002"] == "Error in module <*>: <*>"

    def test_variable_blacklist(self):
        """Test variable blacklisting functionality."""
        persistency = EventPersistency(
            variable_blacklist=[1],  # Blacklist index 1 (second variable)
        )
        persistency.ingest_event(**SAMPLE_EVENT_1)

        data = persistency.get_event_data("E001")
        data["var_0"]
        with pytest.raises(KeyError):
            data["var_1"]

    def test_get_all_variables_method(self):
        """Test the get_all_variables instance method."""
        variables = ["value1", "value2", "value3"]
        named_variables = {"timestamp": "2024-01-01", "level": "INFO"}
        blacklist = [1]  # Blacklist index 1

        persistency = EventPersistency(
            variable_blacklist=blacklist,
        )
        combined = persistency.get_all_variables(variables, named_variables)

        assert "timestamp" in combined
        assert "level" in combined
        assert "var_0" in combined  # First variable
        assert "var_1" not in combined  # Blacklisted
        assert "var_2" in combined  # Third variable

    def test_dict_like_access(self):
        """Test dictionary-like access via __getitem__."""
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)

        data_structure = persistency["E001"]
        assert data_structure is not None
        assert isinstance(data_structure, EventStabilityTracker)


class TestEventPersistencyIntegration:
    """Integration tests for EventPersistency with different backends."""
    def test_tracker_backend_full_workflow(self):
        """Test complete workflow with Tracker backend."""
        persistency = EventPersistency()

        # Ingest events with patterns
        for i in range(20):
            persistency.ingest_event(
                event_id="E001",
                event_template="Test template",
                variables=["constant", str(i)],
                named_variables={},
            )

        # Verify tracker functionality
        data_structure = persistency.event_struct.fast_persistency["E001"]
        assert isinstance(data_structure, EventTracker)

    def test_mixed_event_ids_and_templates(self):
        """Test handling mixed event IDs and templates."""
        persistency = EventPersistency()

        events = [
            ("E001", "Login from <*>", ["192.168.1.1"]),
            ("E002", "Error: <*>", ["timeout"]),
            ("E001", "Login from <*>", ["192.168.1.2"]),
            ("E003", "Logout <*>", ["alice"]),
            ("E002", "Error: <*>", ["connection refused"]),
        ]

        for event_id, template, variables in events:
            persistency.ingest_event(
                event_id=event_id,
                event_template=template,
                variables=variables,
                named_variables={},
            )

        # Verify correct storage
        all_data = persistency.get_events_data()
        assert len(all_data) == 3
        assert len(all_data["E001"].get_data()) == 1
        assert len(all_data["E002"].get_data()) == 1
        assert len(all_data["E003"].get_data()) == 1

        # Verify templates
        templates = persistency.get_event_templates()
        assert templates["E001"] == "Login from <*>"
        assert templates["E002"] == "Error: <*>"
        assert templates["E003"] == "Logout <*>"

    def test_large_scale_ingestion(self):
        """Test ingesting a large number of events."""
        persistency = EventPersistency()

        num_events = 1000
        for i in range(num_events):
            persistency.ingest_event(
                event_id=f"E{i % 10}",
                event_template=f"Template {i % 10}",
                variables=[str(i), str(i * 2)],
                named_variables={"timestamp": f"2024-01-01 10:{i % 60}:00"},
            )

        # Verify all data stored
        all_data = persistency.get_events_data()
        assert len(all_data) == 10

        # Verify counts
        total_rows = sum(len(data_structure.get_data()) for data_structure in all_data.values())
        assert total_rows == 30


class TestEventPersistencyEventsSinceSave:
    def test_events_since_save_starts_at_zero(self):
        p = EventPersistency()
        assert p._events_since_save == 0

    def test_events_since_save_increments_on_ingest(self):
        p = EventPersistency()
        p.ingest_event(**SAMPLE_EVENT_1)
        assert p._events_since_save == 1

    def test_events_since_save_increments_for_no_variable_event(self):
        p = EventPersistency()
        p.ingest_event(event_id="E999", event_template="no vars")
        assert p._events_since_save == 1

    def test_reset_events_since_save(self):
        p = EventPersistency()
        p.ingest_event(**SAMPLE_EVENT_1)
        p.ingest_event(**SAMPLE_EVENT_2)
        p.reset_events_since_save()
        assert p._events_since_save == 0


class TestAggregationUsage:
    def test_equals(self) -> None:
        persistency = EventPersistency()
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        persistency2 = EventPersistency()
        persistency2.ingest_event(**SAMPLE_EVENT_1)
        persistency2.ingest_event(**SAMPLE_EVENT_2)

        persistency3 = EventPersistency()
        persistency3.ingest_event(**SAMPLE_EVENT_2)

        assert persistency == persistency2
        assert persistency != persistency3
