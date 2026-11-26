"""Tests for
detectmatelibrary.utils.persistency.data_structures.trackers.rle_list."""
from detectmatelibrary.utils.persistency.data_structures.trackers.rle_list import RLEList


def test_equal_neighbours_share_a_run():
    rle = RLEList(["A", "A", "B"])
    rle.extend(["B", "B", "C"])

    assert rle.runs() == [("A", 2), ("B", 3), ("C", 1)]
    assert len(rle) == 6
    assert list(rle) == ["A", "A", "B", "B", "B", "C"]


def test_an_empty_list():
    rle = RLEList()
    assert (len(rle), list(rle), rle.runs()) == (0, [], [])


def test_runs_returns_a_copy():
    rle = RLEList([True])
    rle.runs().append((False, 9))
    assert rle.runs() == [(True, 1)]


def test_repr_shows_length_and_a_preview_of_the_runs():
    assert repr(RLEList([True, True, False])) == "RLEList(len=3, runs=[(True, 2), (False, 1)])"
