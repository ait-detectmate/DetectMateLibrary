# flake8: noqa
# mypy: ignore-errors

from typing import TypeAlias, Union

from detectmatelibrary.schemas import schemas_pb2 as pb2
from detectmatelibrary.schemas._op import (
    BASE_SCHEMA,
    LOG_SCHEMA,
    PARSER_SCHEMA,
    DETECTOR_SCHEMA,
    NotSupportedSchema,
    IncorrectSchema,
    NotCompleteSchema,
    initialize,
    initialize_with_default,
    copy,
    serialize,
    deserialize,
    check_is_same_schema,
    check_if_schema_is_complete,
    SchemaID,
    SchemaT
)

# Use the actual protobuf classes for better type hints and IDE support
BaseSchema: TypeAlias = pb2.Schema
LogSchema: TypeAlias = pb2.LogSchema
ParserSchema: TypeAlias = pb2.ParserSchema
DetectorSchema: TypeAlias = pb2.DetectorSchema

# Union type for all schemas (useful for functions that accept any schema)
AnySchema: TypeAlias = Union[BaseSchema, LogSchema, ParserSchema, DetectorSchema]
