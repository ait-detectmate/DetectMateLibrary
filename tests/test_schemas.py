import src.schemas as schemas


class TestSchemas:
    def test_initialize_basic(self):
        schema = schemas.initialize(schemas.BASE_SCHEMA, **{})

        assert schema.__version__ == "1.0.0"


def test_initialize_not_support_schema():
    try:
        schemas.initialize(b"1111", **{})
    except schemas.NotSupportedSchema:
        pass


def test_initialize_log_schema():
    values = {
        "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
    }
    schema = schemas.initialize(schemas.LOG_SCHEMA, **values)

    assert schema.__version__ == "1.0.0"
    assert schema.logID == 1
    assert schema.log == "test"
    assert schema.logSource == "example"
    assert schema.hostname == "example@org"


def test_initialize_parser_schema():
    values = {
        "parserType": "test",
        "EventID": 5,
        "template": "test template",
        "variables": ["a", "b"],
        "parserID": 1,
        "logID": 4,
        "log": "test log",
        "logFormatVariables": {"TimeStamp": "test timestamp"}
    }
    schema = schemas.initialize(schemas.PARSER_SCHEMA, **values)

    assert schema.__version__ == "1.0.0"
    assert schema.EventID == 5
    assert schema.template == "test template"
    assert schema.variables == ["a", "b"]
    assert schema.parserID == 1
    assert schema.logID == 4
    assert schema.log == "test log"
    assert schema.logFormatVariables == {"TimeStamp": "test timestamp"}


def test_initialize_detector_schema():
    values = {
        "detectorID": "test id",
        "detectorType": "type test",
        "alertID": 1,
        "detectionTimestamp": 2,
        "logIDs": [1, 2, 3],
        "predictionLabel": True,
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
    assert schema.predictionLabel
    assert schema.score == 0.5
    assert schema.extractedTimestamps == [4, 5, 6]


def test_serialize_method():
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


def test_serialize_not_supported():
    values = {
        "logID": 1, "log": "test", "logSource": "example", "hostname": "example@org"
    }
    schema = schemas.initialize(schemas.LOG_SCHEMA, **values)

    try:
        schemas.serialize(b"1111", schema=schema)
    except schemas.NotSupportedSchema:
        pass


def test_check_is_same_schema():
    schemas.check_is_same_schema(schemas.LOG_SCHEMA, schemas.LOG_SCHEMA)

    try:
        schemas.check_is_same_schema(schemas.BASE_SCHEMA, schemas.LOG_SCHEMA)
    except schemas.IncorrectSchema:
        pass
