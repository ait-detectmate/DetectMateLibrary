
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
