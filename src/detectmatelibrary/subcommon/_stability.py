from detectmatelibrary.common._config import AutoConfigParams
from detectmatelibrary.utils.persistency.data_structures.trackers.stability import ClassificationMethods

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
