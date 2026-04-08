"""Custom exceptions for DetectMateLibrary.

Use these exceptions in calling code to distinguish library-level errors
from unexpected failures and provide meaningful messages to users.
"""


class DetectMateError(Exception):
    """Base exception for all DetectMateLibrary errors."""


class ComponentRunError(DetectMateError):
    """Raised when an unhandled error occurs inside a component's run() method.

    Wraps the original exception as ``__cause__`` so the full traceback is
    preserved while still allowing callers to catch library errors by type.
    """


class DetectorRunError(ComponentRunError):
    """Raised when an unhandled error occurs inside a detector's detect() method.

    Typically indicates a misconfiguration (e.g. an EventID present in the
    incoming data that is not covered by the detector configuration) or a
    bug in a custom detector implementation.
    """


class ParserRunError(ComponentRunError):
    """Raised when an unhandled error occurs inside a parser's parse() method.

    Typically indicates a format mismatch between the incoming raw log and
    the configured log format, or a bug in a custom parser implementation.
    """
