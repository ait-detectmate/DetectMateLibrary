import logging

import pytest

from detectmatelibrary.utils.sequence_encoding import encode_count_vec, warn_on_window_size_mismatch


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
