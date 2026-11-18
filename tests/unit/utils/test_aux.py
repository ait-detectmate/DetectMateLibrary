"""Tests for detectmatelibrary.utils.aux."""
from datetime import datetime, timezone

from detectmatelibrary.utils import aux
from detectmatelibrary.utils.aux import get_timestamp, time_test_mode


class TestTimestamp:
    def test_test_mode(self) -> None:
        time_test_mode()
        assert get_timestamp() == 0

    def test_no_test_mode_reads_the_clock(self, monkeypatch) -> None:
        class FixedClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 3, 4, 14, 18, 0, 900000, tzinfo=timezone.utc)

        time_test_mode(False)
        monkeypatch.setattr(aux, "datetime", FixedClock)
        assert get_timestamp() == 1772633880  # whole seconds, rounded down
