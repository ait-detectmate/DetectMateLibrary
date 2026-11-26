"""Tests for detectmatelibrary.utils.sequence_encoding."""
import logging

import pytest

from detectmatelibrary.utils.sequence_encoding import encode_count_vec, warn_on_window_size_mismatch
from detectmatelibrary.utils.sequence_encoding import build_count_vec, count_events
from detectmatelibrary import schemas
from detectmatelibrary.utils.sequence_encoding import decode_count_vec


class TestWarnOnWindowSizeMismatch:
    def test_warns_when_restored_keys_use_another_window(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            warn_on_window_size_mismatch("Det", {encode_count_vec(3, (1, 2))}, window_size=4)
        assert any("window_size 3" in r.message for r in caplog.records)

    def test_silent_when_windows_match(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            warn_on_window_size_mismatch("Det", [encode_count_vec(4, (1, 2))], window_size=4)
        assert not caplog.records

    def test_silent_when_nothing_was_restored(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            warn_on_window_size_mismatch("Det", set(), window_size=4)
        assert not caplog.records


class TestBuildCountVec:
    def test_count_events(self):
        assert count_events([0, 1, 4, 0]) == (0, 0, 2, 1, 0, 0, 1)
        assert count_events([3]) == (0, 0, 0, 0, 0, 1)

    def test_build_count_vec(self):
        input_ = [
            schemas.ParserSchema({"eventID": i}) for i in [0, 1, 4, 0]
        ]
        expected = tuple([0, 0, 2, 1, 0, 0, 1])

        assert build_count_vec(input_) == expected


class TestCountEvents:
    def test_slot_layout(self) -> None:
        # slot 0: eventID -2, slot 1: eventID -1, slot e + 2: eventID e
        assert count_events([0, 1, 4, 0]) == (0, 0, 2, 1, 0, 0, 1)
        assert count_events([-1]) == (0, 1)
        assert count_events([-2]) == (1,)
        assert count_events([4, -1, 2, -2, -1]) == (1, 2, 0, 0, 1, 0, 1)

    def test_unparsed_lines_do_not_count_as_another_event(self) -> None:
        assert count_events([3, -1]) != count_events([3, 3])
        assert count_events([-1, 3]) != count_events([0, 3])

    def test_order_does_not_change_the_counts(self) -> None:
        windows = [[4, -1, 2, -2], [-1, 4, -2, 2], [-2, 2, -1, 4], [2, 4, -2, -1]]
        assert len({count_events(w) for w in windows}) == 1

    def test_eventid_below_minus_two_raises(self) -> None:
        with pytest.raises(ValueError, match="-3"):
            count_events([1, -3])


class TestCountVecCodec:
    def test_round_trip(self):
        assert decode_count_vec(encode_count_vec(10, (2, 1, 0, 0, 1))) == (10, (2, 1, 0, 0, 1))

    def test_window_size_distinguishes_identical_vectors(self):
        # The same count vector learned at another window size must not match.
        assert encode_count_vec(4, (1, 1)) != encode_count_vec(8, (1, 1))
