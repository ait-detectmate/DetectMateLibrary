"""The Mongo connector against a real MongoDB (needs_mongo)."""
import detectmatelibrary.schemas.connectors.mongos as mongo_c
import detectmatelibrary.schemas as sc
import pymongo
import pytest


dummy_log_schema = {
    "__version__": "2.0.0",
    "logID": "Log1",
    "log": "Hello world",
    "logSource": "World",
    "hostname": "Hello"
}


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


class TestMongoConnector:
    @pytest.mark.needs_mongo
    def test_insert_data(self, mongo_db):
        args = mongo_c.MongoArgs(url=mongo_db.server, database=mongo_db.name, collection="TestCollection")

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]

        assert col.count_documents({}) == 0

        mongo_c.insert_data("a", [{"b": "test"}], args=args)
        assert col.find_one({"Primary_key": "a"}) is not None
        assert col.count_documents({}) == 1

        mongo_c.insert_data("b", [{"b": "test2"}], args=args)
        assert col.find_one({"Primary_key": "b"}) is not None
        assert col.count_documents({}) == 2

        with pytest.warns(UserWarning):
            mongo_c.insert_data("a", [{"b": "test"}], args=args)
        assert col.find_one({"Primary_key": "a"}) is not None
        assert col.count_documents({}) == 2

        client.close()

    @pytest.mark.needs_mongo
    def test_insert_multiple_data(self, mongo_db):
        args = mongo_c.MongoArgs(url=mongo_db.server, database=mongo_db.name, collection="TestCollection")

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]

        col1 = client[args.database][args.collection + "_1"]

        mongo_c.insert_data("a", [{"d": "test"}, {"c": "hello"}], args=args)
        assert col.count_documents({}) == 1
        assert col1.find_one({"c": "hello"}) is not None
        assert col1.count_documents({}) == 1

        with pytest.warns(UserWarning):
            mongo_c.insert_data("a", [{"d": "test"}, {"c": "hello"}], args=args)

        assert col.count_documents({}) == 1
        assert col1.find_one({"c": "hello"}) is not None
        assert col1.count_documents({}) == 1

        client.close()

    @pytest.mark.needs_mongo
    def test_read_data(self, mongo_db):
        args = mongo_c.MongoArgs(url=mongo_db.server, database=mongo_db.name, collection="TestCollection")

        mongo_c.insert_data("a", [{"d": "test2"}], args=args)
        mongo_c.insert_data("b", [{"d": "test"}, {"c": "hello"}], args=args)

        with pytest.warns(UserWarning):  # Missing subtable
            assert mongo_c.read_data("a", args) == [{"d": "test2"}]

        with pytest.warns(UserWarning):
            no_data = mongo_c.read_data("not_a", args)
        assert no_data == [{}]

        assert mongo_c.read_data("b", args) == [{"d": "test"}, {"c": "hello"}]

    @pytest.mark.needs_mongo
    def test_mongo_connector_log_schema(self, mongo_db):
        sc.set_connector("Mongo", url=mongo_db.url("LogSchema"))

        log_schema = sc.LogSchema(dummy_log_schema).store()
        log_schema2 = sc.LogSchema.from_id(log_schema["logID"])

        assert log_schema == log_schema2

    @pytest.mark.needs_mongo
    def test_mongo_connector_parsed_schema(self, mongo_db):
        sc.set_connector("Mongo", url=mongo_db.url("ParsedSchema"))

        parsed_schema = sc.ParserSchema(dummy_parser_schema).store()
        parsed_schema2 = sc.ParserSchema.from_id(parsed_schema["parsedLogID"])

        assert parsed_schema == parsed_schema2
