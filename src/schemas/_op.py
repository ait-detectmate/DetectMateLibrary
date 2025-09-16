"""" Interface between the code base and the protobuf code."""
import src.schemas.schemas_pb2 as s

from typing import NewType, Tuple, Dict


#  Main variables ************************************
SchemaT = NewType("SchemaT", object)
SchemaID = NewType("SchemaID", bytes)


ANY_SCHEMA: SchemaID = SchemaID(b"0")
LOG_SCHEMA: SchemaID = SchemaID(b"1")
PARSER_SCHEMA: SchemaID = SchemaID(b"2")
DETECTOR_SCHEMA: SchemaID = SchemaID(b"3")


__current_version = "1.0.0"
__id_codes: Dict[SchemaID, SchemaT] = {
    ANY_SCHEMA: s.Schema,  # type: ignore
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


# Private methods *************************************
def __get_schema(schema_id: SchemaID) -> SchemaT | NotSupportedSchema:
    if schema_id not in __id_codes:
        raise NotSupportedSchema()

    return SchemaT(__id_codes[schema_id])


# Main methods *****************************************
def initialize(schema_id: SchemaID, **kwargs) -> SchemaT:
    """Initialize a protobuf schema, it use its arguments and the assigned
    id."""
    kwargs["__version__"] = __current_version
    return __get_schema(schema_id)(**kwargs)  # type: ignore


def serialize(id_schema: SchemaID, schema: SchemaT) -> bytes:
    """Convert the protobuf schema into a binary serialization.

    First 4 bits are the schema id
    """
    return id_schema + schema.SerializeToString()  # type: ignore


def deserialize(message: bytes) -> Tuple[SchemaID, SchemaT]:
    """Return the schema and id from a serialize message."""
    schema = __get_schema(schema_id := SchemaID(message[:1]))()  # type: ignore
    schema.ParseFromString(message[1:])
    return schema_id, schema


def check_is_same_schema(
    id_schema_1: SchemaID, id_schema_2: SchemaID
) -> None | IncorrectSchema:
    """Raise exception if two schemas do not match."""
    if id_schema_1 != id_schema_2:
        raise IncorrectSchema()
    return None
