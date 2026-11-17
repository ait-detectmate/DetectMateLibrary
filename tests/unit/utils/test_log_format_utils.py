"""Tests for detectmatelibrary.utils.log_format_utils."""
from detectmatelibrary.utils.log_format_utils import get_format_variables
import pytest
import re


pytestmark = pytest.mark.usefixtures("frozen_timestamps")


class TestGetFormatVariables:
    def test_no_pattern(self) -> None:
        log = "This is a log."
        var, content = get_format_variables(None, None, log)

        assert var == {"Time": "0"}
        assert content == log

    def test_pattern_no_match(self) -> None:
        pattern = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
        log = "This is a log."

        var, content = get_format_variables(pattern, None, log)

        assert var == {"Time": "0"}
        assert content == log

    def test_pattern_with_match(self) -> None:
        log = "[INFO] 2024-10-05 This is a log."
        pattern = re.compile(r"\[(?P<level>\w+)\]\s(?P<Time>\d{4}-\d{2}-\d{2})")

        var, content = get_format_variables(pattern, None, log)
        assert var == {"level": "INFO", "Time": "2024-10-05"}
        assert content == log

    def test_pattern_with_time_format(self) -> None:
        log = "[INFO] 2024-10-05 14:30:00 This is a log."
        pattern = re.compile(r"\[(?P<level>\w+)\]\s(?P<Time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        time_format = "%Y-%m-%d %H:%M:%S"

        var, content = get_format_variables(pattern, time_format, log)
        assert var == {"level": "INFO", "Time": "1728138600"}
        assert content == log
