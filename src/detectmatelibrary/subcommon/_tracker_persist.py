from detectmatelibrary.common._other_op._persistency_components import PersistConfig
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.persistency_saver import (
    PersistencySaver,
    PersistencySaverConfig,
    load,
    save,
)

from contextlib import nullcontext
from typing import Any, ContextManager


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
