"""Shared pytest configuration for the whole test suite.

Markers (registered in pyproject.toml): `unit`, `contract`, `integration` and
`e2e` come from the test's directory. `slow`, `cli` and `docs` are left out
of the default run by `addopts`; `-m ""` runs everything. `needs_cxx`,
`needs_mongo` and `needs_redis` skip a test locally when the dependency is
missing and fail it in CI (see "Required dependencies" below).

Global-state isolation: every test runs in its own working directory, and
every piece of process-wide state that a test can change is restored after
each test, whatever the test does. See the fixtures in the "Isolation"
section below.
"""
import copy
import functools
import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Callable, Iterator

import fsspec
import numpy as np
import pymongo
import pytest
import redis
from pydantic import BaseModel
from redis.backoff import NoBackoff
from redis.retry import Retry

import detectmatelibrary.schemas._classes as schema_classes
from detectmatelibrary.common.core import CoreComponent
from detectmatelibrary.schemas.connectors.default import ver_record
from detectmatelibrary.utils import aux
from detectmatelibrary.utils.persistency.persistency_saver import _SaveTimer
from tests.support.databases import MONGO_URL, REDIS_HOST, REDIS_PORT, MongoDatabase, RedisDatabases


# ---- Levels -------------------------------------------------------------------
#
# The level marker of a test comes from its directory, so nobody writes it by
# hand: `-m unit`, `-m contract`, `-m integration`, `-m e2e`.

_TESTS_DIR = Path(__file__).resolve().parent
_LEVELS = ("unit", "contract", "integration", "e2e")


@pytest.hookimpl(tryfirst=True)  # before -m deselects by marker
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        try:
            level = item.path.relative_to(_TESTS_DIR).parts[0]
        except ValueError:
            continue
        if level in _LEVELS:
            item.add_marker(getattr(pytest.mark, level))


# ---- Required dependencies ---------------------------------------------------
#
# A test marked needs_cxx / needs_mongo / needs_redis is skipped locally when
# the dependency is missing, and fails in CI (where the CI environment
# variable is set), so a broken runner cannot hide these tests.

_START_SERVICES = "start them with: docker compose -f tests/compose.yaml up -d"


@functools.cache
def _cxx_available() -> bool:
    return shutil.which(os.environ.get("CXX", "g++")) is not None


@functools.cache
def _mongo_available() -> bool:
    try:
        with pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=500) as client:
            client.admin.command("ping")
        return True
    except pymongo.errors.PyMongoError:
        return False


@functools.cache
def _redis_available() -> bool:
    # retry=Retry(NoBackoff(), 0): redis-py retries by default, which turns
    # the 0.5 s timeout into several seconds.
    client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=0.5, socket_timeout=0.5,
        retry=Retry(NoBackoff(), 0),
    )
    try:
        return bool(client.ping())
    except redis.exceptions.RedisError:
        return False
    finally:
        client.close()


_REQUIRED: dict[str, tuple[Callable[[], bool], str]] = {
    "needs_cxx": (_cxx_available, "needs a C++ compiler (g++) for torch.compile"),
    "needs_mongo": (_mongo_available, f"needs MongoDB at {MONGO_URL}; {_START_SERVICES}"),
    "needs_redis": (_redis_available, f"needs Redis at {REDIS_HOST}:{REDIS_PORT}; {_START_SERVICES}"),
}


def _in_ci() -> bool:
    return os.environ.get("CI", "").lower() in ("1", "true", "yes")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden", action="store_true",
        help="rewrite the e2e golden files in tests/test_data/golden/ instead of comparing with them",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--update-golden") and _in_ci():
        raise pytest.UsageError("--update-golden rewrites expected results; it is not allowed in CI")


def pytest_runtest_setup(item: pytest.Item) -> None:
    for marker, (available, reason) in _REQUIRED.items():
        if item.get_closest_marker(marker) is not None and not available():
            if _in_ci():
                pytest.fail(f"{reason} (missing on this CI runner)", pytrace=False)
            pytest.skip(reason)


# ---- Databases --------------------------------------------------------------
#
# Fixed database names on a shared server let two runs (two branches on one
# machine, a re-run in the same CI job) see each other's data. Every database
# test takes its database from one of these fixtures instead. The skip above
# runs before fixtures are set up, so neither touches a missing server.


@pytest.fixture
def mongo_db() -> Iterator[MongoDatabase]:
    """A fresh MongoDB database, dropped after the test."""
    database = MongoDatabase()
    yield database
    with pymongo.MongoClient(database.server, serverSelectionTimeoutMS=2000) as client:
        client.drop_database(database.name)


@pytest.fixture
def redis_dbs() -> Iterator[RedisDatabases]:
    """The Redis test databases, flushed before and after the test."""
    databases = RedisDatabases()
    databases.flush()
    yield databases
    databases.flush()


# ---- Isolation --------------------------------------------------------------


@pytest.fixture
def frozen_timestamps() -> Iterator[None]:
    """Make detectmatelibrary.utils.aux.get_timestamp() return 0 for this
    test."""
    aux.time_test_mode(True)
    yield


@pytest.fixture(autouse=True)
def _isolated_working_directory(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test runs in its own empty working directory.

    Anything written to a relative path (the slow store's .temp/ CSVs, a
    persist path such as ./state, output files) lands there and
    disappears with the test, instead of in the repository. Tests that
    need the repository root as working directory (doc examples) change
    to it explicitly.
    """
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _restore_time_test_mode() -> Iterator[None]:
    """The time test mode is a module global; no test may leak it."""
    saved = aux.test_time
    yield
    aux.time_test_mode(saved)


@pytest.fixture(autouse=True)
def _restore_schema_connector() -> Iterator[None]:
    """set_connector() changes the connector of every schema created
    afterwards; restore it, and the Verification connector's in-memory
    records."""
    connector, url = schema_classes.SCHEMA_CONNECTOR, schema_classes.SCHEMA_URL
    records = copy.deepcopy(ver_record)
    yield
    schema_classes.SCHEMA_CONNECTOR, schema_classes.SCHEMA_URL = connector, url
    ver_record.clear()  # in place: the Verification connector holds this dict
    ver_record.update(records)


@pytest.fixture(autouse=True)
def _restore_numpy_rng() -> Iterator[None]:
    """ECVCDetector reseeds NumPy's global RNG (bug B4); RandomDetector draws
    from it."""
    state = np.random.get_state()
    yield
    np.random.set_state(state)


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """setup_logging() replaces the root handlers; some tests change the root
    level."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.fixture(autouse=True)
def _clear_memory_filesystem() -> Iterator[None]:
    """The memory:// filesystem is process-wide; each test starts with it
    empty."""
    yield
    memory = fsspec.filesystem("memory")
    memory.store.clear()
    memory.pseudo_dirs[:] = [""]


@pytest.fixture(autouse=True)
def _no_leaked_saver_threads() -> Iterator[None]:
    """A PersistencySaver timer left running keeps saving into the next tests'
    storage; stop it and fail the test that started it."""
    before = {t for t in threading.enumerate() if isinstance(t, _SaveTimer)}
    yield
    leaked = [
        t for t in threading.enumerate()
        if isinstance(t, _SaveTimer) and t not in before and t.is_alive()
    ]
    for timer in leaked:
        timer.stop()
    if leaked:
        pytest.fail(
            f"{len(leaked)} PersistencySaver timer thread(s) still running after the test; "
            "stop the saver (saver.stop()) or use the detector in a `with` block."
        )


# ---- B1 guard: shared default configs ---------------------------------------
#
# Bug B1 (see tests/README.md): component constructors use a config *instance*
# as their default argument, so every default-constructed component of a class
# shares it, and set_configuration() mutates it in place. Without this guard,
# one test that configures `NewValueDetector()` changes `NewValueDetector()`
# for every later test.
#
# The guard restores those shared defaults after each test and records which
# tests changed one (printed at the end of the run). It only stops leaks
# *between* tests: B1 itself is still demonstrated by its strict xfail tests,
# which reproduce it inside a single test. Once B1 is fixed, the list stays
# empty and this guard can be deleted.

_default_snapshots: dict[int, tuple[BaseModel, dict[str, Any]]] = {}
_default_changes: list[str] = []


def _component_classes() -> list[type]:
    seen: list[type] = []
    stack: list[type] = [CoreComponent]
    while stack:
        cls = stack.pop()
        if cls not in seen:
            seen.append(cls)
            stack.extend(cls.__subclasses__())
    return seen


def _snapshot(model: BaseModel) -> dict[str, Any]:
    return {
        "dict": copy.deepcopy(model.__dict__),
        "fields_set": set(model.__pydantic_fields_set__),
        "private": copy.deepcopy(model.__pydantic_private__),
        "dump": model.model_dump(),
    }


def _remember_shared_defaults() -> None:
    """Snapshot every pydantic default argument of every component __init__ not
    seen before."""
    for cls in _component_classes():
        init = cls.__dict__.get("__init__")
        defaults = getattr(init, "__defaults__", None) or ()
        kwdefaults = getattr(init, "__kwdefaults__", None) or {}
        for value in (*defaults, *kwdefaults.values()):
            if isinstance(value, BaseModel) and id(value) not in _default_snapshots:
                _default_snapshots[id(value)] = (value, _snapshot(value))


@pytest.fixture(autouse=True)
def _restore_shared_default_configs(request: pytest.FixtureRequest) -> Iterator[None]:
    _remember_shared_defaults()  # classes imported for the first time by earlier tests
    yield
    for model, snap in _default_snapshots.values():
        if model.model_dump() != snap["dump"]:
            model.__dict__.clear()
            model.__dict__.update(copy.deepcopy(snap["dict"]))
            object.__setattr__(model, "__pydantic_fields_set__", set(snap["fields_set"]))
            object.__setattr__(model, "__pydantic_private__", copy.deepcopy(snap["private"]))
            _default_changes.append(f"{request.node.nodeid}: {type(model).__name__}")


def pytest_terminal_summary(terminalreporter):
    if _default_changes:
        terminalreporter.section("shared default configs changed (bug B1)")
        terminalreporter.write_line(
            "These tests changed a component's shared default config; the guard in "
            "tests/conftest.py restored it afterwards:"
        )
        for line in _default_changes:
            terminalreporter.write_line(f"  {line}")
