from detectmatelibrary.utils.persistency.slow_persistency import clean_generated_path
import pytest


def pytest_addoption(parser):
    # These flags opt into test groups that are skipped by default.
    parser.addoption(
        "--run-ignored",
        action="store_true",
        default=False
    )
    parser.addoption(
        "--run-ignored-mongo",
        action="store_true",
        default=False,
        help="Run tests marked ignored_mongo",
    )
    parser.addoption(
        "--run-ignored-redis",
        action="store_true",
        default=False,
        help="Run tests marked ignored_redis",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "ignored: skipped unless --run-ignored is passed")
    config.addinivalue_line(
        "markers", "ignored_mongo: skipped unless --run-ignored-mongo is passed"
    )
    config.addinivalue_line(
        "markers", "ignored_redis: skipped unless --run-ignored-redis is passed"
    )


def pytest_collection_modifyitems(config, items):
    """Skip ignored test groups unless their corresponding flag is passed."""
    for item in items:
        if "ignored" in item.keywords and not config.getoption("--run-ignored"):
            item.add_marker(pytest.mark.skip(reason="Skipped: requires --run-ignored flag"))
        if "ignored_mongo" in item.keywords and not config.getoption("--run-ignored-mongo"):
            item.add_marker(pytest.mark.skip(reason="Skipped: requires --run-ignored-mongo flag"))
        if "ignored_redis" in item.keywords and not config.getoption("--run-ignored-redis"):
            item.add_marker(pytest.mark.skip(reason="Skipped: requires --run-ignored-redis flag"))


def pytest_sessionfinish(session, exitstatus):
    clean_generated_path()
