# conftest.py
import pytest

from pathlib import Path
import os


def pytest_addoption(parser):
    # This creates the command line flag
    parser.addoption(
        "--run-ignored",
        action="store_true",
        default=False
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skips tests tagged as 'ignored' unless flag is passed."""
    if config.getoption("--run-ignored"):
        # If terminal flag is present, don't skip anything
        return

    skip_marker = pytest.mark.skip(reason="Skipped: requires --run-ignored flag")
    for item in items:
        if "ignored" in item.keywords:
            item.add_marker(skip_marker)


def pytest_sessionfinish(session, exitstatus):
    directory = Path(".")
    csv_files = list(directory.glob(".*.csv"))
    for file in csv_files:
        os.remove(file)
