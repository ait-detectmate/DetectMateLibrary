"""" Interface between the code base and the protobuf code."""
from detectmatelibrary.common._config import BasicConfig

import detectmatelibrary.schemas.schemas_pb2 as s


from typing import NewType, Tuple, Dict, Type, Union, Any

from google.protobuf.message import Message


#  Main variables ************************************
# Use Union of actual protobuf classes for better type hints
SchemaT = Union[s.Schema, s.LogSchema, s.ParserSchema, s.DetectorSchema]  #type: ignore
SchemaID = NewType("SchemaID", bytes)


BASE_SCHEMA: SchemaID = SchemaID(b"0")
LOG_SCHEMA: SchemaID = SchemaID(b"1")
PARSER_SCHEMA: SchemaID = SchemaID(b"2")
DETECTOR_SCHEMA: SchemaID = SchemaID(b"3")


__current_version = "1.0.0"
__id_codes: Dict[SchemaID, Type[Message]] = {
    BASE_SCHEMA: s.Schema,  # type: ignore
    LOG_SCHEMA: s.LogSchema,  # type: ignore
    PARSER_SCHEMA: s.ParserSchema,  # type: ignore
    DETECTOR_SCHEMA: s.DetectorSchema,  # type: ignore
}


#  Exceptions ****************************************
class NotSupportedSchema(Exception):
    """The user tries to use a not supported schema."""
    pass


class IncorrectSchema(Exception):
    """Schemas do not match."""
    pass


class NotCompleteSchema(Exception):
    """Not all the fields are full."""
    pass


# Private methods *************************************
def __get_schema_class(schema_id: SchemaID) -> Type[Message]:
    """Get the schema class for the given schema ID."""
    if schema_id not in __id_codes:
        raise NotSupportedSchema()

    return __id_codes[schema_id]


def __is_repeated_field(field: Any) -> bool:
    """Check if a field in the message is a repeated element."""
    return bool(field.is_repeated)


# Main methods *****************************************
def initialize(schema_id: SchemaID, **kwargs: Any) -> SchemaT | NotSupportedSchema:
    """Initialize a protobuf schema, it use its arguments and the assigned
    id."""
    kwargs["__version__"] = __current_version
    schema_class = __get_schema_class(schema_id)
    return schema_class(**kwargs)


def copy(
    schema_id: SchemaID,  schema: SchemaT
) -> SchemaT | IncorrectSchema | NotSupportedSchema:
    """Make a copy of the schema."""
    new_schema = initialize(schema_id=schema_id, **{})
    try:
        new_schema.CopyFrom(schema)  #type: ignore
        return new_schema
    except TypeError:
        raise IncorrectSchema()


def serialize(id_schema: SchemaID, schema: SchemaT) -> bytes:
    """Convert the protobuf schema into a binary serialization.

    First 4 bits are the schema id
    """
    if id_schema not in __id_codes:
        raise NotSupportedSchema()

    return bytes(id_schema + schema.SerializeToString())


def deserialize(message: bytes) -> Tuple[SchemaID, SchemaT]:
    """Return the schema and id from a serialize message."""
    schema_id = SchemaID(message[:1])
    schema_class = __get_schema_class(schema_id)
    schema = schema_class()
    schema.ParseFromString(message[1:])
    return schema_id, schema


# Auxiliar methods *****************************************
def check_is_same_schema(
    id_schema_1: SchemaID, id_schema_2: SchemaID
) -> None | IncorrectSchema:
    """Raise exception if two schemas do not match."""
    if id_schema_1 != id_schema_2:
        raise IncorrectSchema()
    return None


def check_if_schema_is_complete(schema: SchemaT) -> None | NotCompleteSchema:
    """Check if the schema is complete."""
    missing_fields = []
    for field in schema.DESCRIPTOR.fields:
        if not __is_repeated_field(field) and not schema.HasField(field.name):
            missing_fields.append(field.name)

    if len(missing_fields) > 0:
        raise NotCompleteSchema(f"Missing fields: {missing_fields}")

    return None


def get_variables_names(schema: SchemaT) -> list[str]:
    """Get the variable names of the schema."""
    return [field.name for field in schema.DESCRIPTOR.fields]
