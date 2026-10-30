
from .default import VeficationConnector, DefaultConnector
from .mongos import MongoConnector


__all__ = ["VeficationConnector", "DefaultConnector", "MongoConnector"]


def select_connector(connector_name: str = "Default") -> type[DefaultConnector]:
    try:

        return {
            "Verification": VeficationConnector,
            "Default": DefaultConnector,
            "Mongo": MongoConnector,
        }[connector_name]

    except KeyError:
        raise ValueError(f"Connector not found, use one of this {__all__}")
