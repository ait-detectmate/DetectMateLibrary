
from .default import VeficationConnector, DefaultConnector
from .mongos import MongoConnector
from .redis import RedisConnector


__all__ = ["VeficationConnector", "DefaultConnector", "MongoConnector", "RedisConnector"]


def select_connector(connector_name: str = "Default") -> type[DefaultConnector]:
    try:

        return {
            "Verification": VeficationConnector,
            "Default": DefaultConnector,
            "Mongo": MongoConnector,
            "Redis": RedisConnector,
        }[connector_name]

    except KeyError:
        raise ValueError(f"Connector not found, use one of this {__all__}")
