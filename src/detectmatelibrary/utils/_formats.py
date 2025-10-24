from pydantic import BaseModel

from typing import List, Dict, Any, Tuple


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
    variables: List[Variable] = []
    header_variables: List[Header] = []

    @classmethod
    def init(cls, **kwargs):
        for var, cl in zip(["variables", "header_variables"], [Variable, Header]):
            if var in kwargs:
                kwargs[var] = [cl(**var) for var in kwargs[var]]
        return cls(**kwargs)


_formats = {"log_variables": LogVariables}

def choose_format(format: str) -> Tuple[bool, BaseModel | None]:
    return (True, _formats[format]) if format in _formats else (False, None)


def init_format(format: object, params: list):
    return [
        format.init(**param) for param in params
    ]
