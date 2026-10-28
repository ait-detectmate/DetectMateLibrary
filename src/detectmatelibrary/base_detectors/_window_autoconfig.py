"""Window-length auto-configuration shared by the window-based detectors."""
from detectmatelibrary.tools.logging import logger

from ._stability import StabilityAutoConfigParams

from collections import deque
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

if TYPE_CHECKING:
    from .tracker_detector import TrackerDetectorConfig


class SequenceAutoConfigParams(StabilityAutoConfigParams):
    """Configure-phase inputs: the candidate window lengths to try.

    @param min_window_size shortest window length tried during the
           auto-configuration phase. Only used while `fixed_window_size` is None.
    @param max_window_size longest window length tried during the
           auto-configuration phase. The longest length whose sequences are
           classified STABLE or STATIC wins.
    """

    min_window_size: int = Field(
        default=2,
        ge=1,
        description="Shortest window length tried by the configure phase. Must be >= 1.",
    )
    max_window_size: int = Field(
        default=10,
        ge=1,
        description=(
            "Longest window length tried by the configure phase; the longest length whose "
            "sequences are STABLE or STATIC wins. Must be >= min_window_size."
        ),
    )

    @model_validator(mode="after")
    def _validate_window_range(self) -> "SequenceAutoConfigParams":
        if self.max_window_size < self.min_window_size:
            raise ValueError("max_window_size must be >= min_window_size")
        return self


def feed_candidate_windows(
    windows: dict[int, deque[Any]], item: Any, params: SequenceAutoConfigParams
) -> list[tuple[int, deque[Any]]]:
    """Append `item` to one sliding window per candidate length.

    Returns `(length, window)` for every window that is now full.
    Windows are created lazily, so a range changed after construction
    just works.
    """
    full = []
    for length in range(params.min_window_size, params.max_window_size + 1):
        window = windows.setdefault(length, deque(maxlen=length))
        window.append(item)
        if len(window) == length:
            full.append((length, window))
    return full


def choose_window_length(
    name: str, events_data: Mapping[Any, Any], variable: str, params: SequenceAutoConfigParams
) -> int | None:
    """Return the longest candidate length classified STABLE or STATIC.

    `events_data` is keyed by length; `variable` names the tracker inside each
    event. Candidates whose window never filled, or filled fewer than the
    tracker's `min_samples` times, cannot be classified and are skipped.
    Returns None when nothing is stable.
    """
    stable = []
    for length, event_tracker in events_data.items():
        tracker = event_tracker.get_data()[variable]
        if len(tracker.change_series) < tracker.min_samples:
            continue
        if tracker.classify().type in ("STABLE", "STATIC"):
            stable.append(int(length))

    if not stable:
        logger.warning(
            f"[{name}] auto_config=True found no stable window size in "
            f"[{params.min_window_size}..{params.max_window_size}]. "
            "Generating an empty configuration — no instance of this detector is "
            "created and it will neither train nor alert."
        )
        return None

    chosen = max(stable)
    logger.debug(
        f"[{name}] auto_config selected fixed_window_size={chosen} "
        f"from stable candidates {sorted(stable)}."
    )
    return chosen


def warn_if_never_configured(name: str, config: "TrackerDetectorConfig", warned: bool) -> bool:
    """Warn once that an auto-configured detector has no configure phase.

    Callers call this only while no window size is set. Returns True
    once the warning has been logged, now or earlier.
    """
    if warned:
        return True
    if config.auto_config and not config.data_use_configure:
        logger.warning(
            f"[{name}] auto_config=True but data_use_configure is not set, so no configure "
            "phase runs. The detector stays unconfigured and will neither train nor alert."
        )
        return True
    return False
