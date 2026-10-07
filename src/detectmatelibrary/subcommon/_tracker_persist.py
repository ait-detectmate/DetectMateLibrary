from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.persistency_saver import (
    PersistencySaver,
    PersistencySaverConfig,
    load,
    save,
)

from detectmatelibrary.tools.logging import logger

from contextlib import nullcontext
from typing import Any, ContextManager
from pydantic import BaseModel, ConfigDict, Field
import os


class PersistConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Default honors systemd's $STATE_DIRECTORY (set by StateDirectory= in the
    # unit file) so services persist to /var/lib/<dir> with no explicit path=.
    # Falls back to CWD-relative ./state outside systemd. Explicit path= wins.
    path: str = Field(
        default_factory=lambda: next(
            (p for p in os.environ.get("STATE_DIRECTORY", "").split(":") if p.strip()),
            "./state",
        )
    )
    interval_seconds: int = 300
    events_until_save: int | None = None
    auto_load: bool = False
    storage_options: dict[str, Any] = {}


def start_saver(
    name: str, persist: PersistConfig | None, event_persistency: EventPersistency
) -> PersistencySaver | None:
    """Build and start a PersistencySaver for `event_persistency`, or None if
    persist is disabled.

    With `auto_load`, building the saver restores the saved state.
    """
    if persist is None:
        return None
    saver = PersistencySaver(
        event_persistency,
        PersistencySaverConfig(
            path=f"{persist.path}/{name}",
            save_interval_seconds=persist.interval_seconds,
            events_until_save=persist.events_until_save,
            auto_load=persist.auto_load,
            storage_options=persist.storage_options,
        ),
    )
    saver.start()
    return saver


def _guard(saver: PersistencySaver | None) -> ContextManager[Any]:
    """The saver's lock, so state I/O never overlaps a background save."""
    return saver.locked() if saver is not None else nullcontext()


def save_state(
    event_persistency: EventPersistency,
    saver: PersistencySaver | None,
    path: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> bytes | None:
    """Save `event_persistency` to an fsspec URI, or return it as bytes when
    path is None."""
    with _guard(saver):
        return save(event_persistency, path, storage_options)


def load_state(
    event_persistency: EventPersistency,
    saver: PersistencySaver | None,
    path: str | bytes,
    storage_options: dict[str, Any] | None = None,
) -> None:
    """Restore `event_persistency` from an fsspec URI or from bytes returned by
    `save_state`."""
    with _guard(saver):
        load(event_persistency, path, storage_options)


def validate_config_coverage(
        detector_name: str,
        config_events: EventsConfig | dict[str, Any],
        event_persistency: EventPersistency,
) -> None:
    """Log warnings when configured EventIDs or variables have no training
    data.

    Args:
        detector_name: Name of the detector (used in warning messages).
        config_events: The detector's events configuration.
        persistency: The persistency object populated during training.
    """
    config_ids = (
        config_events.events.keys()
        if isinstance(config_events, EventsConfig)
        else config_events.keys()
    )
    if not config_ids:
        return

    events_seen = event_persistency.get_events_seen()
    events_with_data = set(event_persistency.get_events_data().keys())

    for event_id in config_ids:
        if event_id not in events_seen:
            logger.warning(
                f"[{detector_name}] EventID {event_id!r} is configured but was "
                "never observed in training data. Verify that EventIDs in your "
                "config match those produced by the parser."
            )
        elif event_id not in events_with_data:
            logger.warning(
                f"[{detector_name}] EventID {event_id!r} was observed in training "
                "data but no configured variables were extracted. Verify that "
                "variable names/positions in your config match those in the data."
            )
