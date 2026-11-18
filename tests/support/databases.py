"""The MongoDB and Redis servers of the needs_mongo / needs_redis tests, and
the database each test gets on them (fixtures `mongo_db` and `redis_dbs` in
tests/conftest.py).

The servers default to localhost (tests/compose.yaml) and can be moved
with the MONGO_URL and REDIS_URL environment variables.
"""
import os
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import redis

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
_redis_url = urlsplit(os.environ.get("REDIS_URL", "redis://localhost:6379"))
REDIS_HOST, REDIS_PORT = _redis_url.hostname or "localhost", _redis_url.port or 6379
# Redis numbers its databases instead of naming them, so tests get a fixed
# range, kept away from database 0, where a developer's own data usually is.
# Two runs against one Redis at the same time need different REDIS_TEST_DB.
REDIS_FIRST_DB = int(os.environ.get("REDIS_TEST_DB", "10"))
REDIS_DBS_PER_TEST = 3  # the pipeline test keeps parser, detector and aggregator output apart


@dataclass(frozen=True)
class MongoDatabase:
    """A database of its own on the test MongoDB server."""

    server: str = MONGO_URL
    name: str = field(default_factory=lambda: f"detectmate_test_{uuid.uuid4().hex[:12]}")

    def url(self, collection: str) -> str:
        """The connector URL of one collection: <server>/<database>/<collection>."""
        return f"{self.server}/{self.name}/{collection}"


@dataclass(frozen=True)
class RedisDatabases:
    """REDIS_DBS_PER_TEST numbered databases on the test Redis server."""

    host: str = REDIS_HOST
    port: int = REDIS_PORT
    first: int = REDIS_FIRST_DB

    def db(self, i: int = 0) -> int:
        assert 0 <= i < REDIS_DBS_PER_TEST
        return self.first + i

    def url(self, i: int = 0) -> str:
        """The connector URL of database i: http://<host>:<port>:<db>."""
        return f"http://{self.host}:{self.port}:{self.db(i)}"

    def client(self, i: int = 0) -> redis.Redis:
        return redis.Redis(host=self.host, port=self.port, db=self.db(i))

    def flush(self) -> None:
        for i in range(REDIS_DBS_PER_TEST):
            with self.client(i) as client:
                client.flushdb()
