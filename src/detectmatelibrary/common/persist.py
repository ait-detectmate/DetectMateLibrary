from __future__ import annotations

from typing import TYPE_CHECKING

from detectmatelibrary.utils import persistency

if TYPE_CHECKING:
    from detectmatelibrary.common.detector import CoreDetectorConfig


def init_persistency(
    name: str,
    config: "CoreDetectorConfig",
    event_persistency: persistency.EventPersistency,
) -> persistency.PersistencySaver | None:
    """Build and start a PersistencySaver for `event_persistency`, or None if
    disabled."""
    if config.persist is None:
        return None
    p = config.persist
    saver = persistency.PersistencySaver(
        event_persistency,
        persistency.PersistencySaverConfig(
            path=f"{p.path}/{name}",
            save_interval_seconds=p.interval_seconds,
            events_until_save=p.events_until_save,
            auto_load=p.auto_load,
            storage_options=p.storage_options,
        ),
    )
    saver.start()
    return saver
