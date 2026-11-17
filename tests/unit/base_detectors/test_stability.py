"""Tests for detectmatelibrary.base_detectors._stability."""
import logging
import detectmatelibrary.schemas as sc
from detectmatelibrary.detectors.charset_detector import CharsetDetector, CharsetDetectorConfig
from detectmatelibrary.base_detectors import StabilityAutoConfigParams, VariableAutoConfigParams
from detectmatelibrary.base_detectors._stability import TimestampReader
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler
from detectmatelibrary.utils.persistency.data_structures.trackers import ClassificationMethods


def _parser_record(ts_value, event_id=1):
    return sc.ParserSchema({
        "parserType": "test",
        "eventID": event_id,
        "template": "test template",
        "variables": ["abc"],
        "logID": "1",
        "parsedLogID": "1",
        "parserID": "test_parser",
        "log": "test log message",
        "headerVariables": {"ts": ts_value},
    })


_TIME = ClassificationMethods(index=False, time=True)


def _reader(
    classification=_TIME, timestamp_variable="ts", timestamp_format=None
) -> TimestampReader:
    params = StabilityAutoConfigParams(
        classification=classification,
        timestamp_variable=timestamp_variable,
        timestamp_format=timestamp_format,
    )
    return TimestampReader("Det", params, TimeFormatHandler())


class TestTimestampReader:
    def test_returns_none_when_no_method_reads_time(self):
        reader = _reader(classification=ClassificationMethods())
        assert reader.read(_parser_record("2026-08-04 10:00:00")) is None

    def test_parses_iso_timestamp(self):
        assert _reader().read(_parser_record("2026-08-04 10:00:00")) == 1785837600.0

    def test_parses_explicit_format(self):
        """HDFS loghub style, absent from COMMON_TIME_FORMATS."""
        reader = _reader(timestamp_format="%y%m%d %H%M%S")
        first = reader.read(_parser_record("081109 203615"))
        second = reader.read(_parser_record("081109 203645"))
        assert second - first == 30.0

    def test_unparseable_warns_once_and_falls_back(self, caplog):
        reader = _reader()
        with caplog.at_level(logging.WARNING):
            assert reader.read(_parser_record("not-a-time")) is None
            assert reader.read(_parser_record("also-not-a-time")) is None
        warnings = [r for r in caplog.records if "timestamp_variable" in r.message]
        assert len(warnings) == 1
        assert warnings[0].message.startswith("Det: ")

    def test_unset_timestamp_variable_warns_once_and_falls_back(self, caplog):
        """A time-axis classification method without timestamp_variable is an
        operator error, not an opt-out: it must be distinguishable from a
        working time-dependent run, and must not flood the log."""
        reader = _reader(timestamp_variable=None)
        with caplog.at_level(logging.WARNING):
            assert reader.read(_parser_record("2026-08-04 10:00:00")) is None
            assert reader.read(_parser_record("2026-08-04 10:00:01")) is None
        warnings = [r for r in caplog.records if "timestamp_variable" in r.message]
        assert len(warnings) == 1
        assert "not set" in warnings[0].message

    def test_flag_off_stays_silent(self, caplog):
        """No warning when the feature simply is not enabled."""
        reader = _reader(classification=ClassificationMethods(), timestamp_variable=None)
        with caplog.at_level(logging.WARNING):
            assert reader.read(_parser_record("2026-08-04 10:00:00")) is None
        assert not [r for r in caplog.records if "timestamp_variable" in r.message]

    def test_missing_variable_warns_and_falls_back(self, caplog):
        reader = _reader(timestamp_variable="absent")
        with caplog.at_level(logging.WARNING):
            assert reader.read(_parser_record("2026-08-04 10:00:00")) is None
        assert any("timestamp_variable" in r.message for r in caplog.records)

    def test_detector_reads_with_its_auto_config_params(self):
        params = VariableAutoConfigParams(classification=_TIME, timestamp_variable="ts")
        detector = CharsetDetector(config=CharsetDetectorConfig(auto_config_params=params))
        assert detector._timestamps.read(_parser_record("2026-08-04 10:00:00")) == 1785837600.0
