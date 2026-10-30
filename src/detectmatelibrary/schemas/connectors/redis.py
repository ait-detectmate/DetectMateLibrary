from .default import DefaultConnector

from redis.exceptions import ConnectionError, TimeoutError
from redis import Redis

from dataclasses import dataclass
from typing import Any
import warnings
import json


# ---------------- Redis logic
@dataclass
class RedisArgs:
    host: str
    port: int


def __insert(id_: str, data: dict[str, Any], client: Redis) -> None:
    client.hset(
        id_, mapping={key: json.dumps(value) for key, value in data.items()}
    )


def insert_data(id_: str, data: list[dict[str, Any]], args: RedisArgs) -> None:

    try:

        with Redis(host=args.host, port=args.port) as client:
            __insert(id_, data=data[0], client=client)
            for i, data_i in enumerate(data[1:]):
                __insert(f"{id_}_{i + 1}", data=data_i, client=client)

    except (ConnectionError, TimeoutError):
        warnings.warn("Redis server offline, no insertion will be done.")


def read_data(id_: str, args: RedisArgs) -> list[dict[str, Any]]:
    out_: list[dict[bytes, bytes]] = [{}]

    try:

        with Redis(host=args.host, port=args.port) as client:
            out_[0] = client.hgetall(id_)

            if out_ == [{}]:
                warnings.warn(f"No elemt with {id_} found, return empty.")
            else:
                i = 1
                while True:
                    if (aux := client.hgetall(f"{id_}_{i}")) == {}:
                        break
                    out_.append(aux)
                    i += 1

    except (ConnectionError, TimeoutError):
        warnings.warn("Redis server offline, no reading will be done.")

    except Exception as e:
        warnings.warn(f"Not control exception found: {e}")

    finally:
        return [
            {key.decode("utf-8"): json.loads(value) for key, value in o.items()} for o in out_
        ]


# ---------------- Connector interface
class RedisConnector(DefaultConnector):
    def __init__(self, url: str = "None") -> None:
        super().__init__("Redis", url=url)

        self.args = RedisArgs(
            host=(aux := self.url.split("/")[-1].split(":"))[0],
            port=int(aux[1]),
        )

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        insert_data(id_=id_, data=data, args=self.args)

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        return read_data(id_=id_, args=self.args)
