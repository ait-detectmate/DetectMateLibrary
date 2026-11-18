"""Tests for detectmatelibrary.utils.persistency.data_structures.trackers.base.

multi_tracker.
"""
from detectmatelibrary.utils.persistency.data_structures.trackers.base.multi_tracker import MultiTracker
from detectmatelibrary.utils.persistency.data_structures.trackers.base.single_tracker import Classification


class RecordingTracker:
    """A single tracker that keeps what it was given."""

    def __init__(self) -> None:
        self.values: list = []

    def add_value(self, value, timestamp=None) -> None:
        self.values.append((value, timestamp))

    def classify(self) -> Classification:
        return Classification(type="STATIC" if len({v for v, _ in self.values}) == 1 else "RANDOM")

    def __repr__(self) -> str:
        return f"Recording({len(self.values)})"


def test_each_feature_gets_its_own_tracker_on_first_sight():
    multi = MultiTracker(single_tracker_type=RecordingTracker)
    multi.add_data({"user": "alice"}, timestamp=1.0)
    multi.add_data({"user": "bob", "host": "h1"}, timestamp=2.0)

    trackers = multi.get_trackers()
    assert trackers["user"].values == [("alice", 1.0), ("bob", 2.0)]
    assert trackers["host"].values == [("h1", 2.0)]


def test_classify_asks_every_tracker():
    multi = MultiTracker(single_tracker_type=RecordingTracker)
    for user in ("alice", "bob"):
        multi.add_data({"user": user, "host": "h1"})

    assert {name: c.type for name, c in multi.classify().items()} == {"user": "RANDOM", "host": "STATIC"}


def test_repr_lists_the_trackers():
    multi = MultiTracker(single_tracker_type=RecordingTracker)
    multi.add_data({"user": "alice"})
    assert repr(multi) == "MultiTracker{\n\tuser: Recording(1)\n}\n"
