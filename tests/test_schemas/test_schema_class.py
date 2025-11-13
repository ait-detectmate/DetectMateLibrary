from detectmatelibrary.schemas._classes import SchemaVariables
from detectmatelibrary.schemas import PARSER_SCHEMA


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
            "logID": 0,
            "log": "test log",
            "logFormatVariables": {"TimeStamp": "test timestamp"},
            "receivedTimestamp": 0,
            "parsedTimestamp": 0,
        }
        schema_var = SchemaVariables(schema_id=PARSER_SCHEMA, kwargs=values)

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
