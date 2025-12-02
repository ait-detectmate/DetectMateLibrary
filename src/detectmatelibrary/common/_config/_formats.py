from pydantic import BaseModel

from typing_extensions import Self
from typing import Dict, Any


# Sub-formats ********************************************************+
class Variable(BaseModel):
    pos: int
    name: str
    params: Dict[str, Any] = {}


class Header(BaseModel):
    pos: str
    params: Dict[str, Any] = {}


class _LogVariable(BaseModel):
    id: str
    event: int
    template: str
    variables: Dict[int, Variable] = {}
    header_variables: Dict[str, Header] = {}

    @classmethod
    def _init(cls, **kwargs: dict[str, Any]) -> "_LogVariable":
        for var, cl in zip(["variables", "header_variables"], [Variable, Header]):
            if var in kwargs:
                new_dict = {}
                for v in kwargs[var]:
                    aux = cl(**v)  # type: ignore
                    new_dict[aux.pos] = aux
                kwargs[var] = new_dict
        return cls(**kwargs)  # type: ignore

    def get_all(self) -> Dict[Any, Header | Variable]:
        return {**self.variables, **self.header_variables}


# Main-formats ********************************************************+
class LogVariables(BaseModel):
    logvars: Dict[Any, _LogVariable]
    __index: int = 0

    @classmethod
    def _init(cls, params: list[Dict[str, Any]]) -> Self:
        new_dict = {}
        for param in params:
            aux = _LogVariable._init(**param)
            new_dict[aux.event] = aux

        return cls(logvars=new_dict)

    def __next__(self) -> Any | StopIteration:
        if len(keys := list(self.logvars.keys())) > self.__index:
            value = self.logvars[keys[self.__index]]
            self.__index += 1
            return value
        raise StopIteration

    def __iter__(self) -> Self:  # type: ignore
        return self

    def __getitem__(self, idx: str | int) -> _LogVariable | None:
        if idx not in self.logvars:
            return None
        return self.logvars[idx]

    def __contains__(self, idx: str | int) -> bool:
        return idx in self.logvars


class AllLogVariables(BaseModel):
    variables: Dict[int, Variable] = {}
    header_variables: Dict[str, Header] = {}

    @classmethod
    def _init(cls, kwargs: Dict[str, Any]) -> "AllLogVariables":
        for var, cl in zip(["variables", "header_variables"], [Variable, Header]):
            if var in kwargs:
                new_dict = {}
                for v in kwargs[var]:
                    aux = cl(**v)
                    new_dict[aux.pos] = aux
                kwargs[var] = new_dict
        return cls(**kwargs)

    def get_all(self) -> Dict[Any, Header | Variable]:
        return {**self.variables, **self.header_variables}

    def __getitem__(self, idx: Any) -> Self:
        return self

    def __contains__(self, idx: str | int) -> bool:
        return True


# Initialize ********************************************************+
_formats: dict[str, type[LogVariables | AllLogVariables]] = {
    "log_variables": LogVariables,
    "all_log_variables": AllLogVariables
}


def apply_format(format: str, params: Any) -> Any:
    if format in _formats:
        f_cls = _formats[format]
        return f_cls._init(params)  # typr-ignore
    return params
