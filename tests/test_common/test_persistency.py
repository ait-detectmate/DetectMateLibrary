"""Tests for the persistency module core functionality.

This module tests EventPersistency and data structure backends including
EventDataFrame (Pandas) and ChunkedEventDataFrame (Polars).
"""


import pandas as pd
import polars as pl
from detectmatelibrary.common.persistency.event_persistency import EventPersistency
from detectmatelibrary.common.persistency.event_data_structures.dataframes import (
    EventDataFrame,
    ChunkedEventDataFrame,
)
from detectmatelibrary.common.persistency.event_data_structures.trackers import (
    EventTracker,
    StabilityTracker,
)


# Sample test data - variables is a list, not a dict
SAMPLE_EVENT_1 = {
    "event_id": "E001",
    "event_template": "User <*> logged in from <*>",
    "variables": ["alice", "192.168.1.1"],
    "log_format_variables": {"timestamp": "2024-01-01 10:00:00"},
}

SAMPLE_EVENT_2 = {
    "event_id": "E002",
    "event_template": "Error in module <*>: <*>",
    "variables": ["auth", "timeout"],
    "log_format_variables": {"timestamp": "2024-01-01 10:01:00"},
}

SAMPLE_EVENT_3 = {
    "event_id": "E001",
    "event_template": "User <*> logged in from <*>",
    "variables": ["bob", "192.168.1.2"],
    "log_format_variables": {"timestamp": "2024-01-01 10:02:00"},
}


class TestEventPersistency:
    """Test suite for EventPersistency orchestrator class."""

    def test_initialization_with_pandas_backend(self):
        """Test initialization with EventDataFrame backend."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        assert persistency is not None
        assert persistency.event_data_class == EventDataFrame

    def test_initialization_with_polars_backend(self):
        """Test initialization with ChunkedEventDataFrame backend."""
        persistency = EventPersistency(
            event_data_class=ChunkedEventDataFrame,
            event_data_kwargs={"max_rows": 100},
        )
        assert persistency is not None
        assert persistency.event_data_class == ChunkedEventDataFrame

    def test_initialization_with_tracker_backend(self):
        """Test initialization with EventVariableTrackerData backend."""
        persistency = EventPersistency(
            event_data_class=EventTracker,
            event_data_kwargs={"tracker_type": StabilityTracker},
        )
        assert persistency is not None
        assert persistency.event_data_class == EventTracker

    def test_ingest_single_event(self):
        """Test ingesting a single event."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)

        data = persistency.get_event_data("E001")
        assert data is not None
        assert len(data) == 1
        assert "var_0" in data.columns  # alice
        assert "var_1" in data.columns  # 192.168.1.1
        assert "timestamp" in data.columns

    def test_ingest_multiple_events_same_id(self):
        """Test ingesting multiple events with the same ID."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_3)

        data = persistency.get_event_data("E001")
        assert len(data) == 2
        assert data["var_0"].tolist() == ["alice", "bob"]

    def test_ingest_multiple_events_different_ids(self):
        """Test ingesting events with different IDs."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        data1 = persistency.get_event_data("E001")
        data2 = persistency.get_event_data("E002")

        assert len(data1) == 1
        assert len(data2) == 1
        assert "var_0" in data1.columns
        assert "var_0" in data2.columns

    def test_get_all_events_data(self):
        """Test retrieving data for all events."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        all_data = persistency.get_events_data()
        assert "E001" in all_data
        assert "E002" in all_data
        assert isinstance(all_data["E001"], EventDataFrame)
        assert isinstance(all_data["E002"], EventDataFrame)

    def test_template_storage_and_retrieval(self):
        """Test template storage and retrieval."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        template1 = persistency.get_event_template("E001")
        template2 = persistency.get_event_template("E002")

        assert template1 == "User <*> logged in from <*>"
        assert template2 == "Error in module <*>: <*>"

    def test_get_all_templates(self):
        """Test retrieving all templates."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)
        persistency.ingest_event(**SAMPLE_EVENT_2)

        templates = persistency.get_event_templates()
        assert len(templates) == 2
        assert templates["E001"] == "User <*> logged in from <*>"
        assert templates["E002"] == "Error in module <*>: <*>"

    def test_variable_blacklist(self):
        """Test variable blacklisting functionality."""
        persistency = EventPersistency(
            event_data_class=EventDataFrame,
            variable_blacklist=[1],  # Blacklist index 1 (second variable)
        )
        persistency.ingest_event(**SAMPLE_EVENT_1)

        data = persistency.get_event_data("E001")
        assert "var_0" in data.columns  # First variable should be present
        assert "var_1" not in data.columns  # Second variable should be blocked

    def test_get_all_variables_static_method(self):
        """Test the get_all_variables static method."""
        variables = ["value1", "value2", "value3"]
        log_format_variables = {"timestamp": "2024-01-01", "level": "INFO"}
        blacklist = [1]  # Blacklist index 1

        combined = EventPersistency.get_all_variables(
            variables, log_format_variables, blacklist
        )

        assert "timestamp" in combined
        assert "level" in combined
        assert "var_0" in combined  # First variable
        assert "var_1" not in combined  # Blacklisted
        assert "var_2" in combined  # Third variable

    def test_dict_like_access(self):
        """Test dictionary-like access via __getitem__."""
        persistency = EventPersistency(event_data_class=EventDataFrame)
        persistency.ingest_event(**SAMPLE_EVENT_1)

        data_structure = persistency["E001"]
        assert data_structure is not None
        assert isinstance(data_structure, EventDataFrame)


class TestEventDataFrame:
    """Test suite for EventDataFrame (Pandas backend)."""

    def test_initialization(self):
        """Test EventDataFrame initialization."""
        edf = EventDataFrame()
        assert edf is not None
        assert len(edf.data) == 0  # Empty DataFrame

    def test_add_single_data(self):
        """Test adding single data entry."""
        edf = EventDataFrame()
        data_dict = {"user": "alice", "ip": "192.168.1.1"}
        data_df = EventDataFrame.to_data(data_dict)
        edf.add_data(data_df)

        assert edf.data is not None
        assert len(edf.data) == 1
        assert "user" in edf.data.columns

    def test_add_multiple_data(self):
        """Test adding multiple data entries."""
        edf = EventDataFrame()
        edf.add_data(EventDataFrame.to_data({"user": "alice", "ip": "192.168.1.1"}))
        edf.add_data(EventDataFrame.to_data({"user": "bob", "ip": "192.168.1.2"}))

        assert len(edf.data) == 2
        assert edf.data["user"].tolist() == ["alice", "bob"]

    def test_get_data(self):
        """Test retrieving data."""
        edf = EventDataFrame()
        edf.add_data(EventDataFrame.to_data({"user": "alice", "ip": "192.168.1.1"}))

        data = edf.get_data()
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 1

    def test_get_variable_names(self):
        """Test retrieving variable names."""
        edf = EventDataFrame()
        edf.add_data(EventDataFrame.to_data({"user": "alice", "ip": "192.168.1.1", "port": "22"}))

        var_names = edf.get_variables()
        assert "user" in var_names
        assert "ip" in var_names
        assert "port" in var_names


class TestChunkedEventDataFrame:
    """Test suite for ChunkedEventDataFrame (Polars backend)."""

    def test_initialization_default(self):
        """Test ChunkedEventDataFrame initialization with defaults."""
        cedf = ChunkedEventDataFrame()
        assert cedf is not None
        assert cedf.max_rows == 10_000_000
        assert cedf.compact_every == 1000

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        cedf = ChunkedEventDataFrame(max_rows=500, compact_every=100)
        assert cedf.max_rows == 500
        assert cedf.compact_every == 100

    def test_add_single_data(self):
        """Test adding single data entry."""
        cedf = ChunkedEventDataFrame(max_rows=10)
        data_dict = {"user": ["alice"], "ip": ["192.168.1.1"]}
        data_df = ChunkedEventDataFrame.to_data(data_dict)
        cedf.add_data(data_df)

        data = cedf.get_data()
        assert data is not None
        assert len(data) == 1

    def test_add_data_triggers_compaction(self):
        """Test that adding data beyond compact_every triggers compaction."""
        cedf = ChunkedEventDataFrame(max_rows=10000, compact_every=5)

        # Add 6 entries (should trigger compaction at 5)
        for i in range(6):
            cedf.add_data(ChunkedEventDataFrame.to_data({"user": [f"user{i}"], "value": [i]}))

        # After compaction, should have 1 chunk
        data = cedf.get_data()
        assert len(data) == 6

    def test_chunked_storage(self):
        """Test that data is stored in chunks."""
        cedf = ChunkedEventDataFrame(max_rows=5, compact_every=1000)

        # Add more than max_rows
        for i in range(8):
            cedf.add_data(ChunkedEventDataFrame.to_data({"user": [f"user{i}"], "value": [i]}))

        # Should have evicted oldest to stay within max_rows
        data = cedf.get_data()
        assert data is not None
        assert len(data) <= 5

    def test_get_variable_names(self):
        """Test retrieving variable names from chunks."""
        cedf = ChunkedEventDataFrame()
        cedf.add_data(
            ChunkedEventDataFrame.to_data({"user": ["alice"], "ip": ["192.168.1.1"], "port": ["22"]})
        )

        var_names = cedf.get_variables()
        assert "user" in var_names
        assert "ip" in var_names
        assert "port" in var_names

    def test_dict_to_dataframe_conversion(self):
        """Test static method to_data."""
        data_dict = {"user": ["alice"], "ip": ["192.168.1.1"]}
        df = ChunkedEventDataFrame.to_data(data_dict)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert "user" in df.columns


class TestEventPersistencyIntegration:
    """Integration tests for EventPersistency with different backends."""

    def test_pandas_backend_full_workflow(self):
        """Test complete workflow with Pandas backend."""
        persistency = EventPersistency(event_data_class=EventDataFrame)

        # Ingest multiple events
        for i in range(10):
            persistency.ingest_event(
                event_id=f"E{i % 3}",
                event_template=f"Template {i % 3}",
                variables=[str(i), str(i * 10)],
                log_format_variables={},
            )

        # Verify all events stored
        all_data = persistency.get_events_data()
        assert len(all_data) == 3  # 3 unique event IDs

        # Verify correct grouping
        assert len(all_data["E0"].get_data()) == 4  # 0, 3, 6, 9
        assert len(all_data["E1"].get_data()) == 3  # 1, 4, 7
        assert len(all_data["E2"].get_data()) == 3  # 2, 5, 8

    def test_polars_backend_full_workflow(self):
        """Test complete workflow with Polars backend."""
        persistency = EventPersistency(
            event_data_class=ChunkedEventDataFrame,
            event_data_kwargs={"max_rows": 5, "compact_every": 10},
        )

        # Ingest events
        for i in range(10):
            persistency.ingest_event(
                event_id="E001",
                event_template="Test template",
                variables=[str(i)],
                log_format_variables={},
            )

        # Verify data retrieval works
        data = persistency.get_event_data("E001")
        assert data is not None
        assert len(data) <= 5  # Should be trimmed to max_rows

    def test_tracker_backend_full_workflow(self):
        """Test complete workflow with Tracker backend."""
        persistency = EventPersistency(
            event_data_class=EventTracker,
            event_data_kwargs={"tracker_type": StabilityTracker},
        )

        # Ingest events with patterns
        for i in range(20):
            persistency.ingest_event(
                event_id="E001",
                event_template="Test template",
                variables=["constant", str(i)],
                log_format_variables={},
            )

        # Verify tracker functionality
        data_structure = persistency.events_data["E001"]
        assert isinstance(data_structure, EventTracker)

    def test_mixed_event_ids_and_templates(self):
        """Test handling mixed event IDs and templates."""
        persistency = EventPersistency(event_data_class=EventDataFrame)

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
                log_format_variables={},
            )

        # Verify correct storage
        all_data = persistency.get_events_data()
        assert len(all_data) == 3
        assert len(all_data["E001"].get_data()) == 2
        assert len(all_data["E002"].get_data()) == 2
        assert len(all_data["E003"].get_data()) == 1

        # Verify templates
        templates = persistency.get_event_templates()
        assert templates["E001"] == "Login from <*>"
        assert templates["E002"] == "Error: <*>"
        assert templates["E003"] == "Logout <*>"

    def test_large_scale_ingestion(self):
        """Test ingesting a large number of events."""
        persistency = EventPersistency(event_data_class=EventDataFrame)

        num_events = 1000
        for i in range(num_events):
            persistency.ingest_event(
                event_id=f"E{i % 10}",
                event_template=f"Template {i % 10}",
                variables=[str(i), str(i * 2)],
                log_format_variables={"timestamp": f"2024-01-01 10:{i % 60}:00"},
            )

        # Verify all data stored
        all_data = persistency.get_events_data()
        assert len(all_data) == 10

        # Verify counts
        total_rows = sum(len(data_structure.get_data()) for data_structure in all_data.values())
        assert total_rows == num_events

    def test_variable_blacklist_across_backends(self):
        """Test variable blacklist works with different backends."""
        # Blacklist log format variables by name and event variables by index
        log_blacklist = ["timestamp"]
        event_blacklist = [1]  # Second event variable
        blacklist = log_blacklist + event_blacklist

        # Test with Pandas
        p1 = EventPersistency(
            event_data_class=EventDataFrame,
            variable_blacklist=blacklist,
        )
        p1.ingest_event(
            event_id="E001",
            event_template="Test",
            variables=["alice", "1234"],
            log_format_variables={"timestamp": "2024-01-01"},
        )
        data1 = p1.get_event_data("E001")
        assert "var_0" in data1.columns  # First variable
        assert "var_1" not in data1.columns  # Blacklisted
        assert "timestamp" not in data1.columns  # Blacklisted

        # Test with Polars
        p2 = EventPersistency(
            event_data_class=ChunkedEventDataFrame,
            variable_blacklist=blacklist,
        )
        p2.ingest_event(
            event_id="E001",
            event_template="Test",
            variables=["bob", "5678"],
            log_format_variables={"timestamp": "2024-01-02"},
        )
        data2 = p2.get_event_data("E001")
        assert "var_0" in data2.columns  # First variable
        assert "var_1" not in data2.columns  # Blacklisted
        assert "timestamp" not in data2.columns  # Blacklisted
