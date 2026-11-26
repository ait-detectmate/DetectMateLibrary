"""Waiting for background threads without fixed sleeps."""
import time
from typing import Callable


def wait_until(condition: Callable[[], object], timeout: float = 5.0) -> None:
    """Return as soon as condition() is true; fail after timeout seconds.

    The timeout only bounds a broken test: a passing test returns at the
    first poll that sees the condition, however slow the machine.
    """
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(f"condition not met within {timeout} s")
        time.sleep(0.005)
