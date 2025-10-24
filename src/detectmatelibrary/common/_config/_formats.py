from pydantic import BaseModel

from typing import List, Dict, Any, Self


class Variable(BaseModel):
    pos: int
    name: str
    params: Dict[str, Any] = {}


class Header(BaseModel):
    pos: str
    params: Dict[str, Any] = {}


class LogVariables(BaseModel):
    id: str
    event: int
    template: str
    variables: Dict[int, Variable] = {}
    header_variables: Dict[str, Header] = {}

    @classmethod
    def init(cls, **kwargs):
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


class AllLogVariables(BaseModel):
    variables: Dict[int, Variable] = {}
    header_variables: Dict[str, Header] = {}

    @classmethod
    def init(cls, **kwargs):
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


_formats = {
    "log_variables": (LogVariables, True),
    "all_log_variables": (AllLogVariables, False)
}


def apply_format(format: str, params: list | Any) -> Any:
    if format in _formats:
        f_cls, do_dict = _formats[format]
        if do_dict:
            new_dict = {}
            for param in params:
                aux = f_cls.init(**param)
                new_dict[aux.event] = aux
            return new_dict
        else:
            return f_cls.init(**params)
    return params
