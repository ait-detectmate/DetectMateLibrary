import logging

import pytest

from detectmatelibrary.utils.sequence_encoding import (
    count_events,
    encode_count_vec,
    warn_on_window_size_mismatch,
)


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
