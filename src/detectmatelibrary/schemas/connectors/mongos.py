
from .default import DefaultConnector

from pymongo import MongoClient

from dataclasses import dataclass
from typing import Any


@dataclass
class MongoArgs:
    url: str
    database: str
    collection: str


def insert_data(id_: str, data: list[dict[str, Any]], args: MongoArgs) -> None:

    with MongoClient(args.url) as client:
        database = client[args.database]
        for data_i in data:
            database[args.collection].insert_one(data_i)


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
