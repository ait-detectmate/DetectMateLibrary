"""Tests for detectmatelibrary.utils.time_format_handler."""
from datetime import datetime, timezone

import pytest

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


def test_syslog_without_year_assumes_current_year():
    # Expect that a string like 'Nov 11 12:13:14' is parsed with current year
    s = "Nov 11 12:13:14"
    year = datetime.now().year
    dt = datetime.strptime(f"{year} {s}", "%Y %b %d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    assert tfh.parse_timestamp(s) == str(int(dt.timestamp()))
