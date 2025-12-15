import detectmatelibrary.schemas._op as op

from typing_extensions import Self
from typing import Any


class FieldNotFound(Exception):
    def __init__(self, var: str, list_vars: set[str]) -> None:
        super().__init__(f"Field {var} not found in {list_vars}")


def _initialize_schema(
    schema_id: op.SchemaID, kwargs: dict[str, Any] | None
) -> op.SchemaT:

    if kwargs is None:
        _schema = op.initialize(schema_id=schema_id, **{})
    else:
        _schema = op.initialize(schema_id=schema_id, **kwargs)
    return _schema


class SchemaVariables:
    def __init__(
        self, schema_id: op.SchemaID, kwargs: dict[str, Any] | None = None
    ) -> None:
        self.schema_id = schema_id
        self.var_names: set[str]
        self.init_schema(kwargs=kwargs)

    def __contains__(self, idx: str) -> bool:
        return idx in self.var_names

    def get_schema(self) -> op.SchemaT:
        """Retrieve the current schema instance."""
        return _initialize_schema(
            schema_id=self.schema_id,
            kwargs={var: getattr(self, var) for var in self.var_names}
        )

    def set_schema(self, schema: op.SchemaT) -> None:
        """Set the schema instance and update attributes."""
        for var in self.var_names:
            setattr(self, var, getattr(schema, var))

    def init_schema(self, kwargs: dict[str, Any] | None) -> None:
        """Initialize the schema instance and set attributes."""
        _schema = _initialize_schema(schema_id=self.schema_id, kwargs=kwargs)

        var_names = []
        for var in op.get_variables_names(_schema):
            setattr(self, var, getattr(_schema, var))
            var_names.append(var)
        self.var_names = set(var_names)


class BaseSchema(SchemaVariables):
    def __init__(
        self,
        schema_id: op.SchemaID = op.BASE_SCHEMA,
        kwargs: dict[str, Any] | None = None
    ) -> None:
        super().__init__(schema_id=schema_id, kwargs=kwargs)

    def __str__(self) -> str:
        return str(self.get_schema())

    def copy(self) -> "BaseSchema":
        """Create a deep copy of the schema instance."""
        copy_schema = op.copy(schema_id=self.schema_id, schema=self.get_schema())
        new_instance = BaseSchema(schema_id=self.schema_id)
        new_instance.set_schema(copy_schema)
        return new_instance

    def serialize(self) -> bytes:
        """Serialize the schema instance to bytes."""
        return op.serialize(id_schema=self.schema_id, schema=self.get_schema())

    def deserialize(self, message: bytes) -> None | op.IncorrectSchema:
        """Deserialize bytes to populate the schema instance."""
        schema_id, schema = op.deserialize(message=message)

        op.check_is_same_schema(
            id_schema_1=self.schema_id, id_schema_2=schema_id
        )

        self.schema_id = schema_id
        self.set_schema(schema=schema)
        return None

    def check_is_same(self, other: Self) -> None | op.IncorrectSchema:
        """Check if another schema instance is of the same schema type."""
        return op.check_is_same_schema(
            id_schema_1=self.schema_id,
            id_schema_2=other.schema_id
        )

    def __eq__(self, other: object) -> bool:
        """Check equality between two schema instances."""
        if isinstance(other, BaseSchema):
            return self.get_schema() == other.get_schema()  # type: ignore
        return False

    def __getitem__(self, idx: str) -> Any:
        if idx not in self:
            raise FieldNotFound(idx, self.var_names)

        return getattr(self, idx)

    def __setitem__(self, idx: str, value: Any) -> None:
        if idx not in self:
            raise FieldNotFound(idx, self.var_names)

        return setattr(self, idx, value)


# Main schema classes ########################################
class LogSchema(BaseSchema):
    """Log schema class."""
    def __init__(
        self, kwargs: dict[str, Any] | None = None
    ) -> None:
        super().__init__(schema_id=op.LOG_SCHEMA, kwargs=kwargs)

    def copy(self) -> "LogSchema":
        schema: LogSchema = super().copy()  # type: ignore
        return schema


class ParserSchema(BaseSchema):
    """Parser schema class."""
    def __init__(
        self, kwargs: dict[str, Any] | None = None
    ) -> None:
        super().__init__(schema_id=op.PARSER_SCHEMA, kwargs=kwargs)

    def copy(self) -> "ParserSchema":
        schema: ParserSchema = super().copy()  # type: ignore
        return schema


class DetectorSchema(BaseSchema):
    """Detector schema class."""
    def __init__(
        self, kwargs: dict[str, Any] | None = None
    ) -> None:
        super().__init__(schema_id=op.DETECTOR_SCHEMA, kwargs=kwargs)

    def copy(self) -> "DetectorSchema":
        schema: DetectorSchema = super().copy()  # type: ignore
        return schema
