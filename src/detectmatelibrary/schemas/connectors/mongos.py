
from .default import DefaultConnector

from pymongo.errors import ServerSelectionTimeoutError
from pymongo.collection import Collection
from pymongo import MongoClient

from dataclasses import dataclass
from typing import Any
import warnings


@dataclass
class MongoArgs:
    url: str
    database: str
    collection: str


def _insert_single_elemt(id_: str, data: dict[str, Any], collection: Collection) -> None:

    if collection.find_one({id_: data[id_]}) is None:
        collection.insert_one(data)
    else:
        warnings.warn(f"Value with ID {id_} is duplicated, no insertion will be done.")


def insert_data(id_: str, data: list[dict[str, Any]], args: MongoArgs) -> None:
    try:

        with MongoClient(args.url) as client:
            database = client[args.database]
            _insert_single_elemt(id_, data=data[0], collection=database[args.collection])

    except ServerSelectionTimeoutError:
        warnings.warn("Mongo server offline, no insertion will be done.")


class MongoConnector(DefaultConnector):
    def __init__(self, url: str = "None") -> None:
        super().__init__("Mongo", url=url)

        self.args = MongoArgs(
            url="/".join((aux := self.url.split("/"))[:-2]),
            database=aux[-2],
            collection=aux[-1],
        )

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        insert_data(id_=id_, data=data, args=self.args)

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        return [{}]
