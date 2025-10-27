from pydantic import BaseModel

from typing import List, Dict, Any, Self


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
    def init(cls, **kwargs: dict) -> "_LogVariable":
        for var, cl in zip(["variables", "header_variables"], [Variable, Header]):
            if var in kwargs:
                new_dict = {}
                for v in kwargs[var]:
                    aux = cl(**v)
                    new_dict[aux.pos] = aux
                kwargs[var] = new_dict
        return cls(**kwargs)

    def get_all(self) -> List[Header | Variable]:
        return {**self.variables, **self.header_variables}


# Main-formats ********************************************************+
class LogVariables(BaseModel):
    logvars: Dict[str | int, _LogVariable]
    __index: int = 0

    @classmethod
    def init(cls, params):
        new_dict = {}
        for param in params:
            aux = _LogVariable.init(**param)
            new_dict[aux.event] = aux

        return cls(logvars=new_dict)

    def __next__(self) -> Any | StopIteration:
        if len(keys := list(self.logvars.keys())) > self.__index:
            value = self.logvars[keys[self.__index]]
            self.__index += 1
            return value
        raise StopIteration

    def __iter__(self) -> Self:
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
    def init(cls, kwargs):
        for var, cl in zip(["variables", "header_variables"], [Variable, Header]):
            if var in kwargs:
                new_dict = {}
                for v in kwargs[var]:
                    aux = cl(**v)
                    new_dict[aux.pos] = aux
                kwargs[var] = new_dict
        return cls(**kwargs)

    def get_all(self) -> List[Header | Variable]:
        return {**self.variables, **self.header_variables}

    def __getitem__(self, idx) -> Self:
        return self


# Initialize ********************************************************+
_formats = {
    "log_variables": (LogVariables, True),
    "all_log_variables": (AllLogVariables, False)
}


def apply_format(format: str, params: list | Any) -> Any:
    if format in _formats:
        f_cls, do_dict = _formats[format]
        if do_dict:
            return f_cls.init(params)
        else:
            return f_cls.init(params)
    return params
