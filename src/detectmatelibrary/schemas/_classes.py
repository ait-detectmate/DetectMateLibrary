from detectmatelibrary.common._config import BasicConfig
import detectmatelibrary.schemas._op as op

from typing_extensions import Self
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
        self.init_schema(kwargs=kwargs)

    def get_schema(self) -> op.SchemaT:
        return _initialize_schema(
            schema_id=self.schema_id,
            kwargs={var: getattr(self, var) for var in self.var_names}
        )

    def set_schema(self, schema: op.SchemaT) -> None:
        for var in self.var_names:
            setattr(self, var, getattr(schema, var))

    def init_schema(self, kwargs: dict[str, Any] |BasicConfig | None) -> None:
        _schema = _initialize_schema(schema_id=self.schema_id, kwargs=kwargs)

        self.var_names = []
        for var in op.get_variables_names(_schema):
            setattr(self, var, getattr(_schema, var))
            self.var_names.append(var)


class BaseSchema(SchemaVariables):
    def __init__(
        self,
        schema_id: op.SchemaID = op.BASE_SCHEMA,
        kwargs: dict[str, Any] |BasicConfig | None = None
    ) -> None:
        super().__init__(schema_id=schema_id, kwargs=kwargs)

    def copy(self) -> Self:
        copy_schema = op.copy(schema_id=self.schema_id, schema=self.get_schema())
        new_instance = BaseSchema(schema_id=self.schema_id)
        new_instance.set_schema(copy_schema)
        return new_instance

    def serialize(self) -> bytes:
        return op.serialize(id_schema=self.schema_id, schema=self.get_schema())

    def deserialize(self, message: bytes) -> None | op.IncorrectSchema:
        schema_id, schema = op.deserialize(message=message)

        op.check_is_same_schema(
            id_schema_1=self.schema_id, id_schema_2=schema_id
        )

        self.schema_id = schema_id
        self.set_schema(schema=schema)
        return None

    def check_is_same(self, other: Self) -> None | op.IncorrectSchema:
        return op.check_is_same_schema(
            id_schema_1=self.schema_id,
            id_schema_2=other.schema_id
        )  # TODO: add test

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseSchema):
            return False
        return self.get_schema() == other.get_schema()


class LogSchema(BaseSchema):
    def __init__(
        self, kwargs: dict[str, Any] |BasicConfig | None = None
    ) -> None:
        super().__init__(schema_id=op.LOG_SCHEMA, kwargs=kwargs)


class ParserSchema(BaseSchema):
    def __init__(
        self, kwargs: dict[str, Any] |BasicConfig | None = None
    ) -> None:
        super().__init__(schema_id=op.PARSER_SCHEMA, kwargs=kwargs)


class DetectorSchema(BaseSchema):
    def __init__(
        self, kwargs: dict[str, Any] |BasicConfig | None = None
    ) -> None:
        super().__init__(schema_id=op.DETECTOR_SCHEMA, kwargs=kwargs)
