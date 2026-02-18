"""" Interface between the code base and the protobuf code."""
import detectmatelibrary.schemas.schemas_pb2 as s


from typing import NewType, Union, Any


# Use Union of actual protobuf classes for better type hints
SchemaT = Union[s.Schema, s.LogSchema, s.ParserSchema, s.DetectorSchema, s.OutputSchema]  # type: ignore
SchemaID = NewType("SchemaID", bytes)

BASE_SCHEMA: SchemaT = s.Schema  # type: ignore
LOG_SCHEMA: SchemaT = s.LogSchema  # type: ignore
PARSER_SCHEMA: SchemaT = s.ParserSchema  # type: ignore
DETECTOR_SCHEMA: SchemaT = s.DetectorSchema  # type: ignore
OUTPUT_SCHEMA: SchemaT = s.OutputSchema  # type: ignore

__current_version = "1.0.0"


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
def __is_repeated(field: Any) -> bool:
    """Check if a field in the message is a repeated element."""
    return bool(field.is_repeated)


# Auxiliar methods *****************************************
def is_repeated(schema: SchemaT, field_name: str) -> bool:
    """Check if a field is a repeated element."""
    for field in schema.DESCRIPTOR.fields:
        if field.name == field_name:
            return __is_repeated(field)
    raise NotSupportedSchema()


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
        if not __is_repeated(field) and not schema.HasField(field.name):
            missing_fields.append(field.name)

    if len(missing_fields) > 0:
        raise NotCompleteSchema(f"Missing fields: {missing_fields}")

    return None


def get_variables_names(schema: SchemaT) -> list[str]:
    """Get the variable names of the schema."""
    return [field.name for field in schema.DESCRIPTOR.fields]


# Main methods *****************************************
def initialize(schema: SchemaT, **kwargs: Any) -> SchemaT:
    """Initialize a protobuf schema, it uses its arguments and the assigned
    id."""
    kwargs["__version__"] = __current_version
    return schema(**kwargs)


def copy(
    schema_class: SchemaT, schema: SchemaT
) -> SchemaT | IncorrectSchema:
    """Make a copy of the schema."""
    new_schema = initialize(schema_class, **{})
    try:
        new_schema.CopyFrom(schema)
        return new_schema
    except TypeError:
        raise IncorrectSchema()


def serialize(schema: SchemaT) -> bytes:
    return schema.SerializeToString()  # type: ignore


def deserialize(schema_class: SchemaT, message: bytes) -> SchemaT | NotSupportedSchema:
    """Return the schema and id from a serialize message."""
    schema = schema_class()
    try:
        schema.ParseFromString(message)
        return schema
    except Exception:
        raise NotSupportedSchema()
