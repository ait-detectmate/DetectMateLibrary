from detectmatelibrary.common.detector import _extract_timestamp
import detectmatelibrary.schemas as schemas


class TestCoreDetector:
    def test_various_time_formats(self) -> None:
        """Test that _extract_timestamp handles a wide range of realistic time
        formats."""
        dummy_schema = {
            "parserType": "a",
            "EventID": 0,
            "template": "asd",
            "variables": [""],
            "logID": "0",
            "parsedLogID": "22",
            "parserID": "test",
            "log": "This is a parsed log.",
            "logFormatVariables": {"Time": "12121"},
        }
        # Compute expected value for timezone-naive formats at runtime
        EXPECTED_UTC = 1772633880
        test_cases = [
            ("0",                           0),
            ("1772812294",                  1772812294),
            ("1772812294.5",                1772812294),
            # Sub-second epochs: ms, us and ns all fold down to seconds
            ("1772812294000",               1772812294),
            ("1772812294000000",            1772812294),
            ("1772812294000000000",         1772812294),
            ("1772812294000.5",             1772812294),
            # Apache/nginx format
            ("04/Mar/2026:14:18:00 +0000",  EXPECTED_UTC),
            ("04/Mar/2026:14:18:00",        EXPECTED_UTC),
            # ISO 8601 formats
            ("2026-03-04T14:18:00+00:00",   EXPECTED_UTC),
            ("2026-03-04T14:18:00Z",        EXPECTED_UTC),
            ("2026-03-04T14:18:00.000Z",    EXPECTED_UTC),
            ("2026-03-04T14:18:00",         EXPECTED_UTC),
            # Space-separated
            ("2026-03-04 14:18:00",         EXPECTED_UTC),
            ("2026-03-04 14:18:00.000",     EXPECTED_UTC),
            ("2026/03/04 14:18:00",         EXPECTED_UTC),
            # Timezone variations
            ("2026-03-04T15:18:00+01:00",   EXPECTED_UTC),
            ("2026-03-04T13:18:00-01:00",   EXPECTED_UTC),
            # High precision and different separators
            ("2026-03-04T14:18:00.123Z",  EXPECTED_UTC),
            ("2026-03-04 14:18:00,000",   EXPECTED_UTC),
            # Common human-readable variations
            ("Wednesday, March 4, 2026 14:18:00", EXPECTED_UTC),
        ]
        for time_str, expected in test_cases:
            schema = schemas.ParserSchema({**dummy_schema, "logFormatVariables": {"Time": time_str}})
            result = _extract_timestamp(schema)
            assert result == [expected], (
                f"Format '{time_str}': expected [{expected}], got {result}"
            )

    def test_microsecond_epoch_fits_the_schema(self) -> None:
        """Issue #271: a microsecond epoch folded only once landed in
        milliseconds and overflowed the int32 timestamp fields."""
        schema = schemas.DetectorSchema({
            "extractedTimestamps": _extract_timestamp(
                schemas.ParserSchema({"logFormatVariables": {"Time": "1643114452000000"}})
            ),
        })
        assert str(schema)  # rebuilds the protobuf -- used to raise ValueError
        assert schema["extractedTimestamps"] == [1643114452]

    def test_timestamp_fields_hold_more_than_int32(self) -> None:
        """Timestamps are int64, so they survive 2038 (and a stray ms
        value)."""
        for schema, field, value in [
            (schemas.ParserSchema(), "receivedTimestamp", 2**31),
            (schemas.ParserSchema(), "parsedTimestamp", 2**31),
            (schemas.DetectorSchema(), "detectionTimestamp", 2**31),
            (schemas.DetectorSchema(), "receivedTimestamp", 1643114452000),
            (schemas.AggregateSchema(), "outputTimestamp", 2**31),
        ]:
            schema[field] = value
            assert getattr(schema.get_schema(), field) == value
