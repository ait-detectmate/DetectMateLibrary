from detectmatelibrary.schemas._classes import (
    SchemaVariables, BaseSchema_, LogSchema_, ParserSchema_, DetectorSchema_
)
from detectmatelibrary.schemas import (
    PARSER_SCHEMA, BASE_SCHEMA, IncorrectSchema
)

import pytest


class TestSchemaVariables:
    def test_basic_init(self):
        schema_var = SchemaVariables(schema_id=PARSER_SCHEMA)

        assert schema_var.schema_id == PARSER_SCHEMA
        assert schema_var.get_schema().__version__ == "1.0.0"

    def test_init_with_kwargs(self):
        values = {
            "parserType": "test",
            "parserID": "test",
            "EventID": 0,
            "template": "test template",
            "variables": ["a", "b"],
            "parsedLogID": 0,
            "log": "test log",
            "logFormatVariables": {"TimeStamp": "test timestamp"},
            "receivedTimestamp": 0,
            "parsedTimestamp": 0,
        }
        schema_var = SchemaVariables(schema_id=PARSER_SCHEMA, kwargs=values)
        schema_var.logID = 0  # Check if we can add values later

        assert schema_var.parserType == "test"
        assert schema_var.parserID == "test"
        assert schema_var.EventID == 0
        assert schema_var.template == "test template"
        assert schema_var.variables == ["a", "b"]
        assert schema_var.parsedLogID == 0
        assert schema_var.logID == 0
        assert schema_var.log == "test log"
        assert schema_var.logFormatVariables == {"TimeStamp": "test timestamp"}
        assert schema_var.receivedTimestamp == 0
        assert schema_var.parsedTimestamp == 0

    def test_change_value(self):
        schema_var = SchemaVariables(schema_id=PARSER_SCHEMA)

        schema_var.parserType = "new_type"

        assert schema_var.parserType == "new_type"
        assert schema_var.get_schema().parserType == "new_type"

    def test_change_value_list(self):
        schema_var = SchemaVariables(schema_id=PARSER_SCHEMA)

        schema_var.variables = ["x", "y", "z"]
        assert schema_var.variables == ["x", "y", "z"]

        schema_var.variables.append("w")
        assert schema_var.variables == ["x", "y", "z", "w"]
        assert schema_var.get_schema().variables == ["x", "y", "z", "w"]


class TestBaseSchema:
    def test_basic_init(self):
        base_schema = BaseSchema_()

        assert base_schema.schema_id == BASE_SCHEMA
        assert base_schema.get_schema().__version__ == "1.0.0"

    def test_all_initialize(self):
        LogSchema_()
        ParserSchema_()
        DetectorSchema_()

    def test_copy(self):
        log_schema = LogSchema_()
        log_schema.log = "Test log"
        log_schema_copy = log_schema.copy()

        assert log_schema_copy.schema_id == log_schema.schema_id
        assert log_schema_copy.get_schema() == log_schema.get_schema()
        assert log_schema_copy.log == "Test log"

    def test_serialize_deserialize(self):
        log_schema = LogSchema_()
        log_schema.log = "Test log"
        serialized = log_schema.serialize()

        assert isinstance(serialized, bytes)

        new_log_schema = LogSchema_()
        new_log_schema.deserialize(serialized)

        assert new_log_schema.schema_id == log_schema.schema_id
        assert new_log_schema.get_schema() == log_schema.get_schema()
        assert new_log_schema.log == "Test log"

    def test_deserialize_incorrect_schema(self):
        log_schema = LogSchema_()
        serialized = log_schema.serialize()

        parser_schema = ParserSchema_()

        with pytest.raises(IncorrectSchema):
            parser_schema.deserialize(serialized)

    def test_wrong_value(self):
        with pytest.raises(Exception):
            LogSchema_({"logID": "helllo"})

        log_schema = LogSchema_()
        log_schema.logID = "Test log"
        with pytest.raises(Exception):
            log_schema.get_schema()
