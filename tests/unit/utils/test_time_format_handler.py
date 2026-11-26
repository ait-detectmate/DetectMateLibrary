"""Tests for detectmatelibrary.utils.time_format_handler."""
from datetime import datetime, timezone

import pytest

from detectmatelibrary.utils import time_format_handler
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

tfh = TimeFormatHandler()


MARCH_4_2026_1418_UTC = 1772633880


@pytest.mark.parametrize("text, expected", [
    # epochs: seconds, fractions, and ms / us / ns folded down to seconds
    ("0", 0),
    ("1772812294", 1772812294),
    ("1772812294.5", 1772812294),
    ("1772812294000", 1772812294),
    ("1772812294000000", 1772812294),
    ("1772812294000000000", 1772812294),
    ("1772812294000.5", 1772812294),
    ("1600000000000", 1600000000),
    # Apache / nginx
    ("04/Mar/2026:14:18:00 +0000", MARCH_4_2026_1418_UTC),
    ("04/Mar/2026:14:18:00", MARCH_4_2026_1418_UTC),
    ("10/Oct/2000:13:55:36 -0700", 971211336),
    # ISO 8601
    ("2026-03-04T14:18:00+00:00", MARCH_4_2026_1418_UTC),
    ("2026-03-04T14:18:00Z", MARCH_4_2026_1418_UTC),
    ("2026-03-04T14:18:00.000Z", MARCH_4_2026_1418_UTC),
    ("2026-03-04T14:18:00.123Z", MARCH_4_2026_1418_UTC),
    ("2026-03-04T14:18:00", MARCH_4_2026_1418_UTC),
    ("2026-03-04T15:18:00+01:00", MARCH_4_2026_1418_UTC),
    ("2026-03-04T13:18:00-01:00", MARCH_4_2026_1418_UTC),
    # space-separated, with fractions after "." or ","
    ("2026-03-04 14:18:00", MARCH_4_2026_1418_UTC),
    ("2026-03-04 14:18:00.000", MARCH_4_2026_1418_UTC),
    ("2026-03-04 14:18:00,000", MARCH_4_2026_1418_UTC),
    ("2023-01-02 03:04:05,123", 1672628645),
    ("2026/03/04 14:18:00", MARCH_4_2026_1418_UTC),
    # human-readable
    ("Wednesday, March 4, 2026 14:18:00", MARCH_4_2026_1418_UTC),
])
def test_parses_to_epoch_seconds(text, expected):
    """Timezone-less times are read as UTC."""
    assert tfh.parse_timestamp(text) == str(expected)


class _NewYearsEve(datetime):
    """A clock that reads 31 December 2025, 23:59:59."""

    @classmethod
    def now(cls, tz=None):
        return cls(2025, 12, 31, 23, 59, 59, tzinfo=tz)


def test_syslog_without_year_takes_the_current_year(monkeypatch):
    monkeypatch.setattr(time_format_handler, "datetime", _NewYearsEve)
    expected = datetime(2025, 11, 11, 12, 13, 14, tzinfo=timezone.utc)
    assert tfh.parse_timestamp("Nov 11 12:13:14") == str(int(expected.timestamp()))
