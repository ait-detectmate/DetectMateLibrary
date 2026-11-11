
from .default import VerificationConnector, DefaultConnector
from .mongos import MongoConnector
from .redis import RedisConnector


__all__ = ["VerificationConnector", "DefaultConnector", "MongoConnector", "RedisConnector"]


_CONNECTORS: dict[str, type[DefaultConnector]] = {
    "Verification": VerificationConnector,
    "Default": DefaultConnector,
    "Mongo": MongoConnector,
    "Redis": RedisConnector,
}


def select_connector(connector_name: str = "Default") -> type[DefaultConnector]:
    try:
        return _CONNECTORS[connector_name]
    except KeyError:
        raise ValueError(
            f"Connector {connector_name!r} not found, use one of these: {list(_CONNECTORS)}"
        )
