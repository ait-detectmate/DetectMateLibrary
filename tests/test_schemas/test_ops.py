import detectmatelibrary.schemas._op as op_schemas

import pytest


class TestCaseSchemas:
    def test_initialize_basic(self):
        schema = op_schemas.initialize(op_schemas.BASE_SCHEMA, **{})

        assert schema.__version__ == "1.0.0"

    def test_initialize_log_schema(self) -> None:
        values = {
            "logID": "1", "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.logID == "1"
        assert schema.log == "test"
        assert schema.logSource == "example"
        assert schema.hostname == "example@org"

    def test_initialize_parser_schema(self) -> None:
        values = {
            "parserType": "test",
            "parserID": "test",
            "EventID": 5,
            "template": "test template",
            "variables": ["a", "b"],
            "parsedLogID": "2",
            "logID": "4",
            "log": "test log",
            "logFormatVariables": {"TimeStamp": "test timestamp"}
        }
        schema = op_schemas.initialize(op_schemas.PARSER_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.EventID == 5
        assert schema.template == "test template"
        assert schema.variables == ["a", "b"]
        assert schema.parserID == "test"
        assert schema.logID == "4"
        assert schema.parsedLogID == "2"
        assert schema.log == "test log"
        assert schema.logFormatVariables == {"TimeStamp": "test timestamp"}

    def test_initialize_detector_schema(self) -> None:
        values = {
            "detectorID": "test id",
            "detectorType": "type test",
            "alertID": "1",
            "detectionTimestamp": 2,
            "logIDs": ["1", "2", "3"],
            "score": 0.5,
            "extractedTimestamps": [4, 5, 6]
        }
        schema = op_schemas.initialize(op_schemas.DETECTOR_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.detectorID == "test id"
        assert schema.detectorType == "type test"
        assert schema.alertID == "1"
        assert schema.detectionTimestamp == 2
        assert schema.logIDs == ["1", "2", "3"]
        assert schema.score == 0.5
        assert schema.extractedTimestamps == [4, 5, 6]

    def test_initialize_output_schema(self) -> None:
        values = {
            "detectorIDs": ["test id", "another id"],
            "detectorTypes": ["type test", "another type"],
            "alertIDs": ["1", "2"],
            "outputTimestamp": 2,
            "logIDs": ["1", "2", "3"],
            "extractedTimestamps": [4, 5, 6],
            "description": "test description",
            "alertsObtain": {"key": "value"}
        }
        schema = op_schemas.initialize(op_schemas.OUTPUT_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.detectorIDs == ["test id", "another id"]
        assert schema.detectorTypes == ["type test", "another type"]
        assert schema.alertIDs == ["1", "2"]
        assert schema.outputTimestamp == 2
        assert schema.logIDs == ["1", "2", "3"]
        assert schema.extractedTimestamps == [4, 5, 6]
        assert schema.description == "test description"
        assert schema.alertsObtain == {"key": "value"}
        assert schema.extractedTimestamps == [4, 5, 6]

    def test_copy(self) -> None:
        values = {
            "logID": "1", "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)
        schema2 = op_schemas.copy(op_schemas.LOG_SCHEMA, schema)

        assert schema == schema2
        schema.log = "hello"
        assert schema != schema2

    def test_copy_incorrect_schema(self) -> None:
        values = {
            "logID": "1", "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)
        with pytest.raises(op_schemas.IncorrectSchema):
            op_schemas.copy(op_schemas.PARSER_SCHEMA, schema)

    def test_serialize_method(self) -> None:
        values = {
            "logID": "1", "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)
        bschema = op_schemas.serialize(schema=schema)

        new_schema = op_schemas.deserialize(op_schemas.LOG_SCHEMA, bschema)

        assert new_schema.__version__ == "1.0.0"
        assert new_schema.logID == "1"
        assert new_schema.log == "test"
        assert new_schema.logSource == "example"
        assert new_schema.hostname == "example@org"

    def test_check_is_same_schema(self) -> None:
        op_schemas.check_is_same_schema(op_schemas.LOG_SCHEMA, op_schemas.LOG_SCHEMA)

        with pytest.raises(op_schemas.IncorrectSchema):
            op_schemas.check_is_same_schema(op_schemas.BASE_SCHEMA, op_schemas.LOG_SCHEMA)

    def test_check_is_schema_complete(self) -> None:
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **{})
        with pytest.raises(op_schemas.NotCompleteSchema):
            op_schemas.check_if_schema_is_complete(schema)

        values = {
            "logID": "1", "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)
        op_schemas.check_if_schema_is_complete(schema)

    def test_get_variables(self) -> None:
        values = {
            "logID": "1", "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = op_schemas.initialize(op_schemas.LOG_SCHEMA, **values)
        vars = op_schemas.get_variables_names(schema)
        expected_vars = ["logID", "log", "logSource", "hostname", "__version__"]

        assert set(vars) == set(expected_vars), f"{vars}"
        assert len(vars) == len(expected_vars), f"{vars}"

    def test_is_repeated(self) -> None:
        values = {
            "detectorID": "test id",
            "detectorType": "type test",
            "alertID": "1",
            "detectionTimestamp": 2,
            "logIDs": ["1", "2", "3"],
            "score": 0.5,
            "extractedTimestamps": [4, 5, 6]
        }
        schema = op_schemas.initialize(op_schemas.DETECTOR_SCHEMA, **values)

        assert not op_schemas.is_repeated(schema, "detectorID")
        assert not op_schemas.is_repeated(schema, "score")
        assert op_schemas.is_repeated(schema, "logIDs")
        assert op_schemas.is_repeated(schema, "extractedTimestamps")
