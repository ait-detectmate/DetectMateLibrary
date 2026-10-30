
from typing import Any
import logging
import json


def is_list(elem: Any) -> bool:
    return isinstance(elem, list) or type(elem).__name__ == "RepeatedScalarContainer"


def is_dict(elem: Any) -> bool:
    return isinstance(elem, dict) or type(elem).__name__ == "ScalarMapContainer"


def prepare_data(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Prepare data to send to database."""
    num_dics = 0
    out = []
    for key in list(data.keys()):
        value = data[key]
        if is_dict(value):
            num_dics += 1
            data[key] = f"$DICT$_{num_dics}"
            out.append(dict(value))
        elif is_list(value):
            data[key] = "$LIST$_" + json.dumps(list(value))

    return [data] + out


def recover_data(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Recover conversion from database."""
    out = data[0]
    for key, value in out.items():
        if isinstance(value, str):
            if "$DICT$_" in value:
                out[key] = data[int(value.split("_")[-1])]
            elif "$LIST$_" in value:
                out[key] = json.loads(value.split("_")[-1])

    return out


class DefaultConnector:
    def __init__(self, name: str = "Default", url: str = "None") -> None:
        self.name = name
        self.url = url

        logging.debug(str(self))
        if name == "Default":
            # Optimization when connectors are not use
            self.store_data = self.store_data_empty  # type: ignore[method-assign]
            self.restore_data = self.restore_data_empty  # type: ignore[method-assign]

    def __str__(self) -> str:
        return f"Connector <{self.name}> connected to: {self.url}"

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        """Implement method."""
        pass

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        """Implement method."""
        return [{}]

    def store_data(self, id_: str, data: dict[str, Any]) -> None:
        self.to_database(id_, data=prepare_data(data))

    def restore_data(self, id_: str) -> dict[str, Any]:
        return recover_data(self.from_databse(id_))

    def store_data_empty(self, id_: str, data: dict[str, Any]) -> None:
        pass

    def restore_data_empty(self, id_: str) -> dict[str, Any]:
        return {}


ver_record: dict[str, list[dict[str, Any]]] = {}


class VeficationConnector(DefaultConnector):
    """Only use to verify the system offline."""

    def __init__(self, url: str) -> None:
        super().__init__(name="Verification", url=url)

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        ver_record[id_] = data

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        return ver_record[id_]
