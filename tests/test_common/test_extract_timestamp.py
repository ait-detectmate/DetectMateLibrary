from detectmatelibrary.common.detector import _extract_timestamp
import detectmatelibrary.schemas as schemas

class TestCoreDetector:    
    def test_various_time_formats(self) -> None:
            """Test that _extract_timestamp handles a wide range of realistic time formats."""
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
                # Unix timestamps
                ("0",                           0),
                ("1772812294",                  1772812294),
                ("1772812294.5",                1772812294),
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