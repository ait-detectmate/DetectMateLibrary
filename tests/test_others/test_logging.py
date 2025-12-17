import logging
import io
from contextlib import redirect_stdout, redirect_stderr
import pytest

from tools.logging import setup_logging, logger


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration after each test."""
    # Save original state
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    yield
    # Restore original state
    logging.root.handlers = original_handlers
    logging.root.setLevel(original_level)


def test_logging_routing():
    """Test that errors go to stderr and other logs to stdout."""
    # create string buffers to capture output
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # redirect stdout and stderr to our buffers
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        setup_logging(level=logging.DEBUG)

        # test different log levels
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")

    # get the captured output
    stdout_output = stdout_capture.getvalue()
    stderr_output = stderr_capture.getvalue()

    # verify that errors went to stderr
    assert "error" in stderr_output.lower()
    assert "critical" in stderr_output.lower()

    # verify that non-errors went to stdout
    assert "debug" in stdout_output.lower()
    assert "info" in stdout_output.lower()
    assert "warning" in stdout_output.lower()

    # verify that errors didn't go to stdout
    assert "error" not in stdout_output.lower()
    assert "critical" not in stdout_output.lower()


def test_logging_level_filtering():
    """Test that logging level filtering works correctly."""
    # create string buffers to capture output
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # redirect stdout and stderr to our buffers
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        setup_logging(level=logging.INFO)  # set to INFO level

        # test different log levels
        logger.debug("This debug should not appear")
        logger.info("This info should appear")
        logger.warning("This warning should appear")
        logger.error("This error should appear")

    # get the captured output
    stdout_output = stdout_capture.getvalue()
    stderr_output = stderr_capture.getvalue()

    # verify debug messages are filtered out
    assert "debug" not in stdout_output.lower()

    # verify info and warning messages appear in stdout
    assert "info" in stdout_output.lower()
    assert "warning" in stdout_output.lower()

    # verify error messages appear in stderr
    assert "error" in stderr_output.lower()