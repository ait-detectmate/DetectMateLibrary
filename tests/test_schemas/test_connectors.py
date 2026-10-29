
from detectmatelibrary.schemas.connectors.default import ver_record
import detectmatelibrary.schemas as sc

import pytest


dummy_parser_schema = {
    "parserType": "testType",
    "parserID": "Parser_1",
    "eventID": 2,
    "template": "hello there <*>",
    "variables": ["General", "Kenobi"],
    "logID": "log1",
    "log": "hello there General Kenobi",
    "headerVariables": {
        "Time": "-1", "Level": "info"
    },
    "receivedTimestamp": -2,
    "parsedTimestamp": 1,
    "parsedLogID": "Parsed_1",
}


class TestConnectors:
    def test_arguments(self):
        sc.set_connector("Default", url="None", reset_ver=True)
        assert (con := sc.BaseSchema()._conector).name == "Default"
        assert con.url == "None"

        sc.set_connector("Verification", url="A", reset_ver=True)
        assert (con := sc.BaseSchema()._conector).name == "Verification"
        assert con.url == "A"

    def test_incorrect_connector(self):
        with pytest.raises(ValueError):
            sc.set_connector("Incorrect")
            sc.BaseSchema()

    def test_store_data_connector(self):
        sc.set_connector("Verification", reset_ver=True)
        expected = {
            "__version__": "2.0.0",
            "logID": "Log1",
            "log": "Hello world",
            "logSource": "World",
            "hostname": "Hello"
        }
        sc.LogSchema(expected).store()

        assert ver_record == {"Log1": [expected]}

    def test_restore_data(self):
        sc.set_connector("Verification", reset_ver=True)
        expected = {
            "__version__": "2.0.0",
            "logID": "Log1",
            "log": "Hello world",
            "logSource": "World",
            "hostname": "Hello"
        }
        log_schema = sc.LogSchema({"logID": "Log1"})

        ver_record["Log1"] = [expected]
        assert log_schema.restore().as_dict() == expected

    def test_from_id(self):
        sc.set_connector("Verification", reset_ver=True)
        expected = {
            "__version__": "2.0.0",
            "logID": "Log1",
            "log": "Hello world",
            "logSource": "World",
            "hostname": "Hello"
        }
        ver_record["Log1"] = [expected]

        log_schema = sc.LogSchema.from_id("Log1")
        assert isinstance(log_schema, sc.LogSchema)

    def test_check_complex_schema(self):
        sc.set_connector("Verification", reset_ver=True)
        parsed_schema = sc.ParserSchema(dummy_parser_schema).store()

        assert ver_record["Parsed_1"][0] == {
            '__version__': '2.0.0',
            "parserType": "testType",
            "parserID": "Parser_1",
            "eventID": 2,
            "template": "hello there <*>",
            "variables": '$LIST$_["General", "Kenobi"]',
            "logID": "log1",
            "log": "hello there General Kenobi",
            "headerVariables": "$DICT$_1",
            "receivedTimestamp": -2,
            "parsedTimestamp": 1,
            "parsedLogID": "Parsed_1",
        }
        assert ver_record["Parsed_1"][1] == {
            "Time": "-1",
            "Level": "info"
        }

        parsed_schema2 = sc.ParserSchema.from_id("Parsed_1")
        assert parsed_schema == parsed_schema2
