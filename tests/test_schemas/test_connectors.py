
from detectmatelibrary.schemas.connectors.default import verification_dict
import detectmatelibrary.schemas as sc

import pytest


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
            "logID": "Log1",
            "log": "Hello world",
            "logSource": "World",
            "hostname": "Hello"
        }
        sc.LogSchema(expected).store()

        expected["__version__"] = "2.0.0"
        assert verification_dict == {"Log1": expected}

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

        verification_dict["Log1"] = expected
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
        verification_dict["Log1"] = expected

        log_schema = sc.LogSchema.from_id("Log1")
        assert isinstance(log_schema, sc.LogSchema)
