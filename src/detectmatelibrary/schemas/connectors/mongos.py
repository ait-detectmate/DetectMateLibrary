
from .default import DefaultConnector

from pymongo.errors import ServerSelectionTimeoutError
from pymongo.collection import Collection
from pymongo import MongoClient

from dataclasses import dataclass
from typing import Any
import warnings
import logging


# ---------------- Mongo logic
@dataclass
class MongoArgs:
    url: str
    database: str
    collection: str


def _insert_single_elemt(id_: str, data: dict[str, Any], collection: Collection) -> bool:

    data["Primary_key"] = id_
    if collection.find_one({"Primary_key": id_}) is None:
        collection.insert_one(data)
        return True

    warnings.warn(f"Value with ID {id_} is duplicated, no insertion will be done.")
    return False


def insert_data(id_: str, data: list[dict[str, Any]], args: MongoArgs) -> None:
    try:

        with MongoClient(args.url) as client:
            database = client[args.database]
            not_duplicated = _insert_single_elemt(
                id_, data=data[0], collection=database[args.collection]
            )
            if not not_duplicated:
                return None

            for j, data_i in enumerate(data[1:]):
                _insert_single_elemt(
                    id_, data=data_i, collection=database[f"{args.collection}_{j + 1}"]
                )

    except ServerSelectionTimeoutError:
        warnings.warn("Mongo server offline, no insertion will be done.")

    except Exception as e:
        warnings.warn(f"Not control exception found: {e}")


def _read_single_elemt(id_: str, collection: Collection) -> tuple[bool, dict[str, Any]]:
    if (elemt := collection.find_one({"Primary_key": id_})) is None:
        warnings.warn(f"Value with ID {id_} not found, empty elment will be return.")
        return False, {}

    else:
        del elemt["_id"]
        del elemt["Primary_key"]

        return True, elemt


def read_data(id_: str, args: MongoArgs) -> list[dict[str, Any]]:
    out_: list[dict[str, Any]] = [{}]
    try:

        with MongoClient(args.url) as client:
            database = client[args.database]
            was_found, elemt = _read_single_elemt(id_, collection=database[args.collection])
            out_[0] = elemt

            if was_found:
                i = 1
                names = database.list_collection_names()
                while True:
                    if (col_ := f"{args.collection}_{i}") not in names:
                        break
                    i += 1

                    was_found, elemt = _read_single_elemt(id_, collection=database[col_])
                    if was_found:
                        out_.append(elemt)

    except ServerSelectionTimeoutError:
        warnings.warn("Mongo server offline, empty element will be return.")

    except Exception as e:
        warnings.warn(f"Not control exception found: {e}")

    finally:
        return out_


# ---------------- Connector interface

class MongoConnector(DefaultConnector):
    def __init__(self, url: str = "None") -> None:
        super().__init__("Mongo", url=url)

        self.args = MongoArgs(
            url="/".join((aux := self.url.split("/"))[:-2]),
            database=aux[-2],
            collection=aux[-1],
        )

    def to_database(self, id_: str, data: list[dict[str, Any]]) -> None:
        logging.info(f"<<MongoConnector>> sending data from {id_}")
        insert_data(id_=id_, data=data, args=self.args)

    def from_databse(self, id_: str) -> list[dict[str, Any]]:
        logging.info(f"<<MongoConnector>> getting data from {id_}")
        return read_data(id_=id_, args=self.args)
