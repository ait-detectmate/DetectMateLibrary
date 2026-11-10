# flake8: noqa
# --8<-- [start:example_1]
from detectmatelibrary import schemas


log_dict = {"log": "Test log"}

log_schema = schemas.LogSchema(log_dict)
print(log_schema.log == "Test log")  # True

# --8<-- [end:example_1]


# --8<-- [start:example_2]

log_schema = schemas.LogSchema()
log_schema.log = "Test log"
print(log_schema["log"] == log_schema.log)  # True

log_schema2 = schemas.LogSchema()
print(log_schema == log_schema2)  # False

log_schema2.log = "Test log"
print(log_schema == log_schema2)  # True
# --8<-- [end:example_2]


# --8<-- [start:example_3]

log_schema = schemas.LogSchema()
log_schema.log = "Test log"
serialized = log_schema.serialize()
print(isinstance(serialized, bytes))  # True

new_log_schema = schemas.LogSchema()
new_log_schema.deserialize(serialized)
print(new_log_schema == log_schema)  # True
# --8<-- [end:example_3]


# --8<-- [start:example_4]
from detectmatelibrary.schemas import set_connector

set_connector(
    connector="Mongo",  # Connector name, e.g. "Mongo" or "Redis"
    url="mongodb://localhost:27017/TestDataset/test",  # Connector URL
)

parsed_schema = schemas.ParserSchema({"parsedLogID": "ciao"}).store()
parsed_schema2 = schemas.ParserSchema.from_id(parsed_schema["parsedLogID"])

print(parsed_schema == parsed_schema2)  # True

# --8<-- [end:example_4]


# --8<-- [start:example_5]

set_connector(
    connector="Default",  # Global connector: stores nothing
    url="None",  # Global URL
)

# This schema overrides the global setup and uses the verification connector
parsed_schema = schemas.ParserSchema(
    {"parsedLogID": "ciao"},
    connector="Mongo",  # Override name
    url="mongodb://localhost:27017/TestDataset/test",  # Override URL
).store()

# from_id() uses the global (default) connector, which stored nothing
parsed_schema2 = schemas.ParserSchema.from_id(parsed_schema["parsedLogID"])
print(parsed_schema == parsed_schema2)  # False

# A schema with the same override reads back what was stored
parsed_schema3 = schemas.ParserSchema(
    {"parsedLogID": "ciao"},
    connector="Verification",
    url="NewURL",
).restore()
print(parsed_schema == parsed_schema3)  # True

# --8<-- [end:example_5]
