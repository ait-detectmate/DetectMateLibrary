
from typing import Any


class DefaultConnector:
    def __init__(self, name: str = "Default", url: str = "None") -> None:
        self.name = name
        self.url = url

    def __str__(self) -> str:
        return f"Connector <{self.name}> connected to: {self.url}"

    def store_data(self, id_: str, data: dict[str, Any]) -> None:
        pass

    def restore_data(self, id_: str) -> dict[str, Any]:
        return {}


class VeficationConnector(DefaultConnector):
    """Only use to verify the system offline."""

    def __init__(self, url: str) -> None:
        super().__init__(name="Verification", url=url)
        self._dict: dict[str, dict[str, Any]] = {}

    def store_data(self, id_: str, data: dict[str, Any]) -> None:
        self._dict[id_] = data

    def restore_data(self, id_: str) -> dict[str, Any]:
        return self._dict[id_]
