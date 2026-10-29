
from .default import VeficationConnector, DefaultConnector


__all__ = ["VeficationConnector", "DefaultConnector"]


def select_connector(connector_name: str = "Default") -> type[DefaultConnector]:
    try:
        return {
            "Verification": VeficationConnector,
            "Default": DefaultConnector,
        }[connector_name]
    except KeyError:
        raise ValueError(f"Connector not found, use one of this {__all__}")
