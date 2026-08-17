"""Tests for EventPersistency.events_seen tracking."""

from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.event_data_structures.trackers import EventStabilityTracker


class TestEventsSeen:
    """Test that events_seen tracks all event IDs passed to ingest_event()."""

    def setup_method(self) -> None:
        self.persistency = EventPersistency(event_data_class=EventStabilityTracker)

    def test_events_seen_recorded_on_early_return(self) -> None:
        """Event ID is tracked even when variables are empty (early-return
        path)."""
        self.persistency.ingest_event(
            event_id="E1",
            event_template="some template",
            variables=[],
            named_variables={}
        )
        assert "E1" in self.persistency.get_events_seen()
        assert "E1" not in self.persistency.get_events_data()

    def test_events_seen_recorded_with_data(self) -> None:
        """Event ID is tracked when variables are present."""
        self.persistency.ingest_event(
            event_id="E2",
            event_template="some template",
            named_variables={"status": "ok"}
        )
        assert "E2" in self.persistency.get_events_seen()
        assert "E2" in self.persistency.get_events_data()

    def test_events_seen_not_duplicated(self) -> None:
        """Repeated calls for the same event ID produce a single entry."""
        for _ in range(5):
            self.persistency.ingest_event(
                event_id=42,
                event_template="t",
                named_variables={"x": "v"}
            )
        assert len(self.persistency.get_events_seen()) == 1
        assert 42 in self.persistency.get_events_seen()

    def test_events_seen_tracks_multiple_ids(self) -> None:
        """Multiple distinct event IDs are all tracked."""
        for eid in [1, 2, 3]:
            self.persistency.ingest_event(
                event_id=eid,
                event_template="t",
                named_variables={"x": str(eid)}
            )
        assert self.persistency.get_events_seen() == {1, 2, 3}

    def test_get_events_seen_returns_set(self) -> None:
        """get_events_seen() returns a set."""
        result = self.persistency.get_events_seen()
        assert isinstance(result, set)

    def test_events_seen_mixed_empty_and_nonempty(self) -> None:
        """Events seen with and without data are both in events_seen."""
        self.persistency.ingest_event(event_id=1, event_template="t")
        self.persistency.ingest_event(event_id=2, event_template="t", named_variables={"k": "v"})
        assert {1, 2} == self.persistency.get_events_seen()
        assert set(self.persistency.get_events_data().keys()) == {2}
