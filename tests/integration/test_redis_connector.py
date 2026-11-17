"""The Redis connector against a real Redis (needs_redis)."""
import detectmatelibrary.schemas.connectors.redis as redis_c
import detectmatelibrary.schemas as sc
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


class TestRedisConnector:
    @pytest.mark.needs_redis
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

    @pytest.mark.needs_redis
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

    @pytest.mark.needs_redis
    def test_redis_connector_log_schema(self):
        sc.set_connector("Redis", url="http://localhost:6379:0")
        client = redis.Redis(host="localhost", port=6379)
        client.flushdb()

        assert client.hgetall(dummy_log_schema["logID"]) == {}
        client.close()

        log_schema = sc.LogSchema(dummy_log_schema).store()
        log_schema2 = sc.LogSchema.from_id(log_schema["logID"])

        assert log_schema == log_schema2

    @pytest.mark.needs_redis
    def test_redis_connector_parsed_schema(self):
        sc.set_connector("Redis", url="http://localhost:6379:0")
        client = redis.Redis(host="localhost", port=6379)
        client.flushdb()

        assert client.hgetall(dummy_parser_schema["parsedLogID"]) == {}
        client.close()

        parsed_schema = sc.ParserSchema(dummy_parser_schema).store()
        parsed_schema2 = sc.ParserSchema.from_id(parsed_schema["parsedLogID"])

        assert parsed_schema == parsed_schema2
