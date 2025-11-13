from detectmatelibrary.common._config import BasicConfig
import detectmatelibrary.schemas._op as op

from typing import Any


def _initialize_schema(
    schema_id: op.SchemaID, kwargs: dict[str, Any] |BasicConfig | None
) -> op.SchemaT:
        if kwargs is None:
            _schema = op.initialize(schema_id=schema_id, **{})
        elif isinstance(kwargs, BasicConfig):
            _schema = op.initialize_with_default(
                schema_id=schema_id, config=kwargs
            )
        else:
            _schema = op.initialize(schema_id=schema_id, **kwargs)
        return _schema


class SchemaVariables:
    def __init__(
        self, schema_id: op.SchemaID, kwargs: dict[str, Any] |BasicConfig | None = None
    ) -> None:
        self.schema_id = schema_id
        _schema = _initialize_schema(schema_id=self.schema_id, kwargs=kwargs)

        self.var_names = []
        for var in op.get_variables_names(_schema):
            setattr(self, var, getattr(_schema, var))
            self.var_names.append(var)

    def get_schema(self) -> op.SchemaT:
        return _initialize_schema(
            schema_id=self.schema_id,
            kwargs={var: getattr(self, var) for var in self.var_names}
        )

    def set_schema(self, schema: op.SchemaT) -> None:
        self._schema = schema


class BaseSchema(SchemaVariables):
    def __init__(
        self, schema_id: op.SchemaID = op.BASE_SCHEMA, kwargs: dict[str, Any] |BasicConfig | None = None
    ) -> None:
        super().__init__(schema_id=schema_id, kwargs=kwargs)

    #def copy(self) -> "BaseSchema":
    #    return op.copy(schema_id=self.schema_id, schema=self.get_schema())

    def serialize(self) -> bytes:
        return op.serialize(id_schema=self.schema_id, schema=self.get_schema())

    def deserialize(self, message: bytes) -> None:
        schema_id, schema = op.deserialize(message=message)
        self.schema_id = schema_id
        self.set_schema(schema=schema)

    def is_same(self, other: "BaseSchema") -> None | op.IncorrectSchema:
        return op.check_is_same_schema(
            id_schema_1=self.schema_id, id_schema_2=other.schema_id
        )

    def is_complete(self) -> None | op.NotCompleteSchema:
        return op.check_if_schema_is_complete(schema=self.get_schema())
