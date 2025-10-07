"""" Interface between the code base and the protobuf code."""
from src.utils.aux import BasicConfig

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


class NotCompleteSchema(Exception):
    """Not all the fields are full."""
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


def initialize_with_default(schema_id: SchemaID, config: BasicConfig) -> SchemaT:
    """Initialize schema with default fields in a Config instance."""
    fields = initialize(schema_id=schema_id, **{}).DESCRIPTOR.fields
    args = {}
    dict_config = config.get_config()
    for field in fields:
        if field.name in dict_config:
            args[field.name] = dict_config[field.name]

    return initialize(schema_id=schema_id, **args)


def serialize(id_schema: SchemaID, schema: SchemaT) -> bytes:
    """Convert the protobuf schema into a binary serialization.

    First 4 bits are the schema id
    """
    if id_schema not in __id_codes:
        raise NotSupportedSchema()

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


def check_if_schema_is_complete(schema: SchemaT) -> None | NotCompleteSchema:
    """Check if the schema is complete."""
    for field in schema.DESCRIPTOR.fields:
        if not getattr(schema, field.name):
            raise NotCompleteSchema(field.name)
