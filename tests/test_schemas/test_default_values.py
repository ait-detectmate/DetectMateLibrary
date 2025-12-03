import detectmatelibrary.schemas._op as op_schemas


class TestCaseDefaultValues:
    """Tests done to check that all the ints can work with zeros."""
    def test_log_schema(self) -> None:
        values = {
            "logID": 0, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)
        op_schemas.check_if_schema_is_complete(schema)

    def test_initialize_parser_schema(self) -> None:
        values = {
            "parserType": "test",
            "parserID": "test",
            "EventID": 0,
            "template": "test template",
            "variables": ["a", "b"],
            "parsedLogID": 0,
            "logID": 0,
            "log": "test log",
            "logFormatVariables": {"TimeStamp": "test timestamp"},
            "receivedTimestamp": 0,
            "parsedTimestamp": 0,
        }
        schema = op_schemas.initialize(op_schemas.PARSER_SCHEMA, **values)
        op_schemas.check_if_schema_is_complete(schema)

    def test_initialize_detector_schema(self) -> None:
        values = {
            "detectorID": "test id",
            "detectorType": "type test",
            "alertID": 0,
            "detectionTimestamp": 0,
            "logIDs": [0, 0, 0],
            "score": 0.0,
            "extractedTimestamps": [0, 0, 0],
            "description": "",
            "receivedTimestamp": 0,
        }
        schema = op_schemas.initialize(op_schemas.DETECTOR_SCHEMA, **values)
        op_schemas.check_if_schema_is_complete(schema)

    def test_initialize_parser_schema_empty_list_dict(self) -> None:
        values = {
            "parserType": "test",
            "parserID": "test",
            "EventID": 0,
            "template": "test template",
            "parsedLogID": 0,
            "logID": 0,
            "log": "test log",
            "receivedTimestamp": 0,
            "parsedTimestamp": 0,
        }
        schema = op_schemas.initialize(op_schemas.PARSER_SCHEMA, **values)
        op_schemas.check_if_schema_is_complete(schema)

        assert len(schema.logFormatVariables) == 0
        assert len(schema.variables) == 0
