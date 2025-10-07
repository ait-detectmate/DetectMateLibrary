"""" Interface between the code base and the protobuf code."""
import src.schemas.schemas_pb2 as s


from typing import NewType, Tuple, Dict, Type, Union
from google.protobuf.message import Message


#  Main variables ************************************
# Use Union of actual protobuf classes for better type hints
SchemaT = Union[s.Schema, s.LogSchema, s.ParserSchema, s.DetectorSchema]
SchemaID = NewType("SchemaID", bytes)


BASE_SCHEMA: SchemaID = SchemaID(b"0")
LOG_SCHEMA: SchemaID = SchemaID(b"1")
PARSER_SCHEMA: SchemaID = SchemaID(b"2")
DETECTOR_SCHEMA: SchemaID = SchemaID(b"3")


__current_version = "1.0.0"
__id_codes: Dict[SchemaID, Type[Message]] = {
    BASE_SCHEMA: s.Schema,
    LOG_SCHEMA: s.LogSchema,
    PARSER_SCHEMA: s.ParserSchema,
    DETECTOR_SCHEMA: s.DetectorSchema,
}


#  Exceptions ****************************************
class NotSupportedSchema(Exception):
    """The user tries to use a not supported schema."""
    pass


class IncorrectSchema(Exception):
    """Schemas do not match."""
    pass


# Private methods *************************************
def __get_schema_class(schema_id: SchemaID) -> Type[Message]:
    """Get the schema class for the given schema ID."""
    if schema_id not in __id_codes:
        raise NotSupportedSchema()
    return __id_codes[schema_id]


# Main methods *****************************************
def initialize(schema_id: SchemaID, **kwargs) -> SchemaT:
    """Initialize a protobuf schema, it use its arguments and the assigned
    id."""
    kwargs["__version__"] = __current_version
    schema_class = __get_schema_class(schema_id)
    return schema_class(**kwargs)


def initialize_with_defaul(schema_id: SchemaID, config) -> SchemaT:
    pass


def serialize(id_schema: SchemaID, schema: SchemaT) -> bytes:
    """Convert the protobuf schema into a binary serialization.

    First 4 bits are the schema id
    """
    return id_schema + schema.SerializeToString()


def deserialize(message: bytes) -> Tuple[SchemaID, SchemaT]:
    """Return the schema and id from a serialize message."""
    schema_id = SchemaID(message[:1])
    schema_class = __get_schema_class(schema_id)
    schema = schema_class()
    schema.ParseFromString(message[1:])
    return schema_id, schema


def check_is_same_schema(
    id_schema_1: SchemaID, id_schema_2: SchemaID
) -> None | IncorrectSchema:
    """Raise exception if two schemas do not match."""
    if id_schema_1 != id_schema_2:
        raise IncorrectSchema()
    return None
