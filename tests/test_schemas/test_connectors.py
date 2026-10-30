
from detectmatelibrary.schemas.connectors.default import ver_record
import detectmatelibrary.schemas.connectors.mongos as mongo_c
import detectmatelibrary.schemas.connectors.redis as redis_c

import detectmatelibrary.schemas as sc

import pymongo
import redis

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


class TestConnectors:
    def test_arguments(self):
        sc.set_connector("Default", url="None", reset_ver=True)
        assert (con := sc.BaseSchema()._conector).name == "Default"
        assert con.url == "None"

        sc.set_connector("Verification", url="A", reset_ver=True)
        assert (con := sc.BaseSchema()._conector).name == "Verification"
        assert con.url == "A"

    def test_arguments_priority(self):
        sc.set_connector("Default", url="None", reset_ver=True)

        assert (con := sc.BaseSchema(connector="Verification", url="A")._conector).name == "Verification"
        assert con.url == "A"

    def test_incorrect_connector(self):
        with pytest.raises(ValueError):
            sc.set_connector("Incorrect")
            sc.BaseSchema()

    def test_store_data_connector(self):
        sc.set_connector("Verification", reset_ver=True)
        expected = dummy_log_schema
        sc.LogSchema(expected).store()

        assert ver_record == {"Log1": [expected]}

    def test_restore_data(self):
        sc.set_connector("Verification", reset_ver=True)
        expected = dummy_log_schema
        log_schema = sc.LogSchema({"logID": "Log1"})

        ver_record["Log1"] = [expected]
        assert log_schema.restore().as_dict() == expected

    def test_from_id(self):
        sc.set_connector("Verification", reset_ver=True)
        expected = dummy_log_schema
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


class TestMongoConnector:
    @pytest.mark.ignored_mongo
    def test_insert_data(self):
        args = mongo_c.MongoArgs(
            url="mongodb://localhost:27017",
            database="TestDataset",
            collection="TestCollection"
        )

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]
        col.delete_many({})

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

    @pytest.mark.ignored_mongo
    def test_insert_mutliple_data(self):
        args = mongo_c.MongoArgs(
            url="mongodb://localhost:27017",
            database="TestDataset",
            collection="TestCollection"
        )

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]
        col.delete_many({})

        col1 = client[args.database][args.collection + "_1"]
        col1.delete_many({})

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

    @pytest.mark.ignored_mongo
    def test_read_data(self):
        args = mongo_c.MongoArgs(
            url="mongodb://localhost:27017",
            database="TestDataset",
            collection="TestCollection"
        )

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]
        col.delete_many({})

        col1 = client[args.database][args.collection + "_1"]
        col1.delete_many({})

        mongo_c.insert_data("a", [{"d": "test2"}], args=args)
        mongo_c.insert_data("b", [{"d": "test"}, {"c": "hello"}], args=args)

        with pytest.warns(UserWarning):  # Missing subtable
            assert mongo_c.read_data("a", args) == [{"d": "test2"}]

        with pytest.warns(UserWarning):
            no_data = mongo_c.read_data("not_a", args)
        assert no_data == [{}]

        assert mongo_c.read_data("b", args) == [{"d": "test"}, {"c": "hello"}]

        client.close()

    @pytest.mark.ignored_mongo
    def test_mongo_connector_log_schema(self):
        sc.set_connector(
            "Mongo", url="mongodb://localhost:27017/TestDataset/LogSchema"
        )
        args = mongo_c.MongoArgs(
            url="mongodb://localhost:27017",
            database="TestDataset",
            collection="LogSchema"
        )

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]
        col.delete_many({})

        log_schema = sc.LogSchema(dummy_log_schema).store()
        log_schema2 = sc.LogSchema.from_id(log_schema["logID"])

        client.close()

        assert log_schema == log_schema2

    @pytest.mark.ignored_mongo
    def test_mongo_connector_parsed_schema(self):
        sc.set_connector(
            "Mongo", url="mongodb://localhost:27017/TestDataset/ParsedSchema"
        )
        args = mongo_c.MongoArgs(
            url="mongodb://localhost:27017",
            database="TestDataset",
            collection="ParsedSchema"
        )

        client = pymongo.MongoClient(args.url)
        col = client[args.database][args.collection]
        col.delete_many({})

        parsed_schema = sc.ParserSchema(dummy_parser_schema).store()
        parsed_schema2 = sc.ParserSchema.from_id(parsed_schema["parsedLogID"])

        client.close()

        assert parsed_schema == parsed_schema2


class TestRedisConnector:
    @pytest.mark.ignored_redis
    def test_insert_data(self):
        client = redis.Redis(host="localhost", port=6379)
        client.flushdb()

        assert client.hgetall("a") == {}

        args = redis_c.RedisArgs(host="localhost", port=6379, db=0)
        redis_c.insert_data("a", [{"b": "test"}], args=args)
        redis_c.insert_data("b", [{"b": "test"}, {"d": "time"}], args=args)

        assert client.hgetall("a") == {b"b": b'"test"'}
        assert client.hgetall("b") == {b"b": b'"test"'}
        assert client.hgetall("b_1") == {b"d": b'"time"'}

        client.close()

    @pytest.mark.ignored_redis
    def test_read_data(self):
        client = redis.Redis(host="localhost", port=6379)
        client.flushdb()

        assert client.hgetall("a") == {}
        client.close()

        args = redis_c.RedisArgs(host="localhost", port=6379, db=0)
        redis_c.insert_data("a", [{"b": "test", "c": 0.2}], args=args)
        redis_c.insert_data("b", [{"b": "test"}, {"d": "time"}], args=args)

        assert redis_c.read_data("a", args) == [{"b": "test", "c": 0.2}]

        with pytest.warns(UserWarning):
            redis_c.read_data("not_a", args)

        assert redis_c.read_data("b", args) == [{"b": "test"}, {"d": "time"}]

    @pytest.mark.ignored_redis
    def test_redis_connector_log_schema(self):
        sc.set_connector("Redis", url="http://localhost:6379:0")
        client = redis.Redis(host="localhost", port=6379)
        client.flushdb()

        assert client.hgetall(dummy_log_schema["logID"]) == {}
        client.close()

        log_schema = sc.LogSchema(dummy_log_schema).store()
        log_schema2 = sc.LogSchema.from_id(log_schema["logID"])

        assert log_schema == log_schema2

    @pytest.mark.ignored_redis
    def test_mongo_connector_parsed_schema(self):
        sc.set_connector("Redis", url="http://localhost:6379:0")
        client = redis.Redis(host="localhost", port=6379)
        client.flushdb()

        assert client.hgetall(dummy_parser_schema["parsedLogID"]) == {}
        client.close()

        parsed_schema = sc.ParserSchema(dummy_parser_schema).store()
        parsed_schema2 = sc.ParserSchema.from_id(parsed_schema["parsedLogID"])

        assert parsed_schema == parsed_schema2
