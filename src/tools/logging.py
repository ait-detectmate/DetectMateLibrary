import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logging(
    level: int = logging.INFO,
    logfile: Optional[str] = None,
    *, 
    force_color: Optional[bool] = None
) -> None:
    # determine whether to use colors
    if force_color is None:
        use_color = sys.stdout.isatty()
    else:
        use_color = bool(force_color)

    # common plain formatter for file and non-colored console
    plain_fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    colored_fmt = logging.Formatter(
        '\033[95m[%(asctime)s] %(levelname)s %(name)s\033[0m: %(message)s'
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # remove existing handlers to avoid duplicates on repeated setup calls
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # console handler: stdout for non-error, stderr for error
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    stdout_handler.setFormatter(colored_fmt if use_color else plain_fmt)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(colored_fmt if use_color else plain_fmt)

    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)

    # optional file handler (always plain)
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(level)
        file_handler.setFormatter(plain_fmt)
        root_logger.addHandler(file_handler)