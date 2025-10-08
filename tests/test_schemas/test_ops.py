from src.utils.aux import BasicConfig

import src.schemas as schemas

import pytest


class MockConfig(BasicConfig):
    score: float = 0.4
    detectorID: str = "test"
    no_field: str = "should not appear"


class TestCaseSchemas:
    def test_initialize_basic(self):
        schema = schemas.initialize(schemas.BASE_SCHEMA, **{})

        assert schema.__version__ == "1.0.0"

    def test_initialize_not_support_schema(self) -> None:
        try:
            schemas.initialize(b"1111", **{})
        except schemas.NotSupportedSchema:
            pass

    def test_initialize_log_schema(self) -> None:
        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.logID == 1
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
            "parsedLogID": 2,
            "logID": 4,
            "log": "test log",
            "logFormatVariables": {"TimeStamp": "test timestamp"}
        }
        schema = schemas.initialize(schemas.PARSER_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.EventID == 5
        assert schema.template == "test template"
        assert schema.variables == ["a", "b"]
        assert schema.parserID == "test"
        assert schema.logID == 4
        assert schema.parsedLogID == 2
        assert schema.log == "test log"
        assert schema.logFormatVariables == {"TimeStamp": "test timestamp"}

    def test_initialize_detector_schema(self) -> None:
        values = {
            "detectorID": "test id",
            "detectorType": "type test",
            "alertID": 1,
            "detectionTimestamp": 2,
            "logIDs": [1, 2, 3],
            "score": 0.5,
            "extractedTimestamps": [4, 5, 6]
        }
        schema = schemas.initialize(schemas.DETECTOR_SCHEMA, **values)

        assert schema.__version__ == "1.0.0"
        assert schema.detectorID == "test id"
        assert schema.detectorType == "type test"
        assert schema.alertID == 1
        assert schema.detectionTimestamp == 2
        assert schema.logIDs == [1, 2, 3]
        assert schema.score == 0.5
        assert schema.extractedTimestamps == [4, 5, 6]

    def test_initialize_with_default(self) -> None:
        schema = schemas.initialize_with_default(schemas.DETECTOR_SCHEMA, MockConfig())
        expected_schema = schemas.initialize(
            schema_id=schemas.DETECTOR_SCHEMA, **{"score": 0.4, "detectorID": "test"}
        )

        assert schema == expected_schema

    def test_copy(self) -> None:
        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)
        schema2 = schemas.copy(schemas.LOG_SCHEMA, schema)

        assert schema == schema2
        schema.log = "hello"
        assert schema != schema2

    def test_copy_incorrect_schema(self) -> None:
        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)
        with pytest.raises(schemas.IncorrectSchema):
            schemas.copy(schemas.PARSER_SCHEMA, schema)

    def test_copy_incompatible_schema(self) -> None:
        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)
        with pytest.raises(schemas.NotSupportedSchema):
            schemas.copy(b"213123213123", schema)

    def test_serialize_method(self) -> None:
        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)
        bschema = schemas.serialize(schemas.LOG_SCHEMA, schema=schema)

        schema_id, new_schema = schemas.deserialize(bschema)

        assert schema_id == schemas.LOG_SCHEMA

        assert new_schema.__version__ == "1.0.0"
        assert new_schema.logID == 1
        assert new_schema.log == "test"
        assert new_schema.logSource == "example"
        assert new_schema.hostname == "example@org"

    def test_serialize_not_supported(self) -> None:
        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)

        with pytest.raises(schemas.NotSupportedSchema):
            schemas.serialize(b"1111", schema=schema)

    def test_check_is_same_schema(self) -> None:
        schemas.check_is_same_schema(schemas.LOG_SCHEMA, schemas.LOG_SCHEMA)

        with pytest.raises(schemas.IncorrectSchema):
            schemas.check_is_same_schema(schemas.BASE_SCHEMA, schemas.LOG_SCHEMA)

    def test_check_is_schema_complete(self) -> None:
        schema = schemas.initialize(schemas.LOG_SCHEMA, **{})
        with pytest.raises(schemas.NotCompleteSchema):
            schemas.check_if_schema_is_complete(schema)

        values = {
            "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
        }
        schema = schemas.initialize(schemas.LOG_SCHEMA, **values)
        schemas.check_if_schema_is_complete(schema)
