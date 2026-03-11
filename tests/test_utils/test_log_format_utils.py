from datetime import datetime, timezone

from detectmatelibrary.utils.log_format_utils import generate_logformat_regex
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

tfh = TimeFormatHandler()


class TestGenerateLogformatRegex:
    def test_simple_format(self):
        headers, regex = generate_logformat_regex("<Time> <Content>")
        assert headers == ["Time", "Content"]
        m = regex.match("2024-01-01 hello world")
        assert m is not None
        assert m.group("Time") == "2024-01-01"
        assert m.group("Content") == "hello world"

    def test_special_characters_in_format_literals(self):
        """Parentheses in literal parts of the format must be treated as literals,
        not as regex group delimiters.  This is the root cause of the LOGIN bug:
        the format 'type=<Type> msg=audit(<Time>): <Content>' previously generated
        a regex where the '(' before <Time> opened an unnamed capture group,
        causing Time to capture '(1642723741.076:377)' (with parentheses) instead
        of '1642723741.076:377'."""
        log_format = "type=<Type> msg=audit(<Time>): <Content>"
        headers, regex = generate_logformat_regex(log_format)

        audit_lines = [
            ("type=USER_ACCT msg=audit(1642723741.072:375): pid=10125 uid=0",
             "USER_ACCT", "1642723741.072:375", "pid=10125 uid=0"),
            ("type=CRED_ACQ msg=audit(1642723741.072:376): pid=10125 uid=0",
             "CRED_ACQ", "1642723741.072:376", "pid=10125 uid=0"),
            ("type=LOGIN msg=audit(1642723741.076:377): pid=10125 uid=0 old-auid=4294967295 auid=0 tty=(none) old-ses=4294967295 ses=65 res=1",
             "LOGIN", "1642723741.076:377", "pid=10125 uid=0 old-auid=4294967295 auid=0 tty=(none) old-ses=4294967295 ses=65 res=1"),
        ]
        for log, expected_type, expected_time, expected_content in audit_lines:
            m = regex.match(log)
            assert m is not None, f"No match for log: {log!r}"
            assert m.group("Type") == expected_type
            # Time must NOT include the surrounding parentheses
            assert m.group("Time") == expected_time, (
                f"Time for '{expected_type}' should be '{expected_time}', "
                f"got '{m.group('Time')}' (parentheses not properly escaped)"
            )
            assert m.group("Content") == expected_content

    def test_timestamp_extraction_from_audit_format(self):
        """After the fix, the extracted Time value must be parseable as a
        float-based Unix timestamp (as used in _extract_timestamp)."""
        log_format = "type=<Type> msg=audit(<Time>): <Content>"
        _, regex = generate_logformat_regex(log_format)

        log = "type=LOGIN msg=audit(1642723741.076:377): pid=10125 uid=0 res=1"
        m = regex.match(log)
        assert m is not None
        time_val = m.group("Time")
        # _extract_timestamp does: int(float(time_val.split(":")[0]))
        time_part = time_val.split(":")[0]
        parsed = int(float(time_part))
        assert parsed == 1642723741

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
