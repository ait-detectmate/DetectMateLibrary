from .default import DefaultConnector

from redis.exceptions import ConnectionError, TimeoutError
from redis import Redis

from dataclasses import dataclass
from typing import Any
import warnings


@dataclass
class RedisArgs:
    host: str
    port: int


def insert_data(id_: str, data: list[dict[str, Any]], args: RedisArgs) -> None:

    try:

        with Redis(host=args.host, port=args.port) as client:
            client.hset(id_, mapping=data)

    except (ConnectionError, TimeoutError):
        warnings.warn("Redis server offline, no insertion will be done.")


class RedisConnector(DefaultConnector):
    pass
