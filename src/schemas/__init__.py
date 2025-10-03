# flake8: noqa

from typing import TypeAlias, NewType

from src.schemas._op import (
    BASE_SCHEMA,
    LOG_SCHEMA,
    PARSER_SCHEMA,
    DETECTOR_SCHEMA,
    NotSupportedSchema,
    IncorrectSchema,
    initialize,
    serialize,
    deserialize,
    check_is_same_schema,
    SchemaID,
    SchemaT
)

BaseSchema = NewType("BaseSchema", SchemaT)
LogSchema = NewType("LogSchema", SchemaT)
ParserSchema = NewType("ParserSchema", SchemaT)
DetectorSchema = NewType("DetectorSchema", SchemaT)
