from datetime import datetime, timezone

from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

tfh = TimeFormatHandler()

def test_iso_z():
    s = "2023-01-02T03:04:05Z"
    expected = int(datetime.fromisoformat("2023-01-02T03:04:05+00:00").timestamp())
    assert tfh.parse_timestamp(s) == str(expected)


def test_iso_ms_z():
    s = "2023-01-02T03:04:05.123Z"
    expected = int(datetime.fromisoformat("2023-01-02T03:04:05.123000+00:00").timestamp())
    assert tfh.parse_timestamp(s) == str(expected)


def test_comma_millis():
    s = "2023-01-02 03:04:05,123"
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S,%f")
    dt = dt.replace(tzinfo=timezone.utc)
    assert tfh.parse_timestamp(s) == str(int(dt.timestamp()))


def test_apache_format():
    s = "10/Oct/2000:13:55:36 -0700"
    dt = datetime.strptime(s, "%d/%b/%Y:%H:%M:%S %z")
    assert tfh.parse_timestamp(s) == str(int(dt.timestamp()))


def test_epoch_seconds_and_millis():
    s_sec = "1600000000"
    s_millis = "1600000000000"
    assert tfh.parse_timestamp(s_sec) == "1600000000"
    assert tfh.parse_timestamp(s_millis) == "1600000000"


def test_syslog_without_year_assumes_current_year():
    # Expect that a string like 'Nov 11 12:13:14' is parsed with current year
    s = "Nov 11 12:13:14"
    year = datetime.now().year
    dt = datetime.strptime(f"{year} {s}", "%Y %b %d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    assert tfh.parse_timestamp(s) == str(int(dt.timestamp()))
