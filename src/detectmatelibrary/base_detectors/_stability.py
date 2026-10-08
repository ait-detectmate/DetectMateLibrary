from detectmatelibrary.common._config import AutoConfigParams

from detectmatelibrary.utils.persistency.data_structures.trackers.stability import ClassificationMethods
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

from detectmatelibrary.schemas import ParserSchema
from detectmatelibrary.tools.logging import logger

from pydantic import Field


class StabilityAutoConfigParams(AutoConfigParams):
    classification: ClassificationMethods = ClassificationMethods()
    timestamp_variable: str | None = Field(
        default=None,
        description=(
            "Header variable (from the parser's log_format) holding each event's time. "
            "Required by the time and slope_time classification methods."
        ),
    )
    timestamp_format: str | None = Field(
        default=None,  # None -> TimeFormatHandler auto-detect
        description="Format of timestamp_variable. None detects it automatically.",
    )


class TimestampReader:
    """Reads each record's event time for time-axis stability classification.

    `params` is read on every call, so later changes to it apply.
    """

    def __init__(
        self, detector_name: str, params: StabilityAutoConfigParams, handler: TimeFormatHandler
    ) -> None:
        self._detector_name = detector_name
        self._params = params
        self._handler = handler
        self._warned = False

    def read(self, input_: ParserSchema) -> float | None:
        """The record's event time, or None if no enabled classification method
        reads the time axis or the time cannot be read."""
        if not self._params.classification.needs_timestamps:
            return None

        if not self._params.timestamp_variable:
            self._warn_once(
                "a time-axis classification method is enabled "
                "but timestamp_variable is not set"
            )
            return None

        raw = input_["logFormatVariables"].get(self._params.timestamp_variable)
        ts = self._handler.parse_timestamp(str(raw or ""), self._params.timestamp_format)
        if ts == "0":
            self._warn_once(
                f"timestamp_variable {self._params.timestamp_variable!r} is missing or "
                f"unparseable (got {raw!r})"
            )
            return None

        return float(ts)

    def _warn_once(self, reason: str) -> None:
        """Log the first time-dependent misconfiguration, then stay quiet.

        A bad config would otherwise emit one warning per record, so the
        flag latches after the first message.
        """
        if self._warned:
            return
        self._warned = True
        logger.warning(
            "%s: %s; falling back to the index axis for stability classification.",
            self._detector_name, reason,
        )
