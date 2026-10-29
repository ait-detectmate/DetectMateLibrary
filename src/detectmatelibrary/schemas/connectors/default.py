
from typing import Any


def prepare_data(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Prepare data to send to database."""
    return [data]


def recover_data(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Recover conversion from database."""
    return data[0]


class DefaultConnector:
    def __init__(self, name: str = "Default", url: str = "None") -> None:
        self.name = name
        self.url = url

    def __str__(self) -> str:
        return f"Connector <{self.name}> connected to: {self.url}"

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        pass

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        return [{}]

    def store_data(self, id_: str, data: dict[str, Any]) -> None:
        self.to_database(id_, data=prepare_data(data))

    def restore_data(self, id_: str) -> dict[str, Any]:
        return recover_data(self.from_databse(id_))


ver_record: dict[str, list[dict[str, Any]]] = {}


class VeficationConnector(DefaultConnector):
    """Only use to verify the system offline."""

    def __init__(self, url: str) -> None:
        super().__init__(name="Verification", url=url)

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        ver_record[id_] = data

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        return ver_record[id_]
