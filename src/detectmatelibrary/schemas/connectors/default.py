
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


verification_dict: dict[str, dict[str, Any]] = {}


class VeficationConnector(DefaultConnector):
    """Only use to verify the system offline."""

    def __init__(self, url: str) -> None:
        super().__init__(name="Verification", url=url)

    def store_data(self, id_: str, data: dict[str, Any]) -> None:
        verification_dict[id_] = data

    def restore_data(self, id_: str) -> dict[str, Any]:
        return verification_dict[id_]
