from detectmatelibrary.tools.logging import logger

from .event_persistency import EventPersistency
from .persistency_saver import load, save

from typing import Any, Callable, Protocol


# Core Component ##################################################################

class Stoppable(Protocol):
    """Structural type for objects ``Component`` will stop on context-manager
    exit.

    Decouples ``Component`` from any concrete saver implementation: a subclass
    may assign anything with a ``stop()`` method to ``self.saver`` (today the
    only such type is ``PersistencySaver``) without ``common.core`` having to
    import the persistency package. This preserves the dependency direction
    detectmate -> persistency, not the reverse.
    """
    def stop(self) -> None: ...


class PersistencyOp:
    @staticmethod
    def __get_persistency(instance: object) -> EventPersistency | None:
        ep = getattr(instance, "persistency", None)
        if ep is None:
            logger.debug("No persistency configured, nothing to export")
        return ep

    @staticmethod
    def __apply(
        instance: object,
        op: Callable[[EventPersistency, Any, dict[str, Any] | None], bytes | None],
        path: Any = None,
        storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:

        if (ep := PersistencyOp.__get_persistency(instance)) is None:
            return None

        saver = getattr(instance, "saver", None)
        if saver is not None:
            with saver.locked():
                return op(ep, path, storage_options)
        return op(ep, path, storage_options)

    @staticmethod
    def save(
        instance: object,
        path: str | None = None,
        storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:
        """Save this component's EventPersistency state.

        When path is None, returns the state as bytes (zip archive).
        When path is given, writes to that fsspec URI and returns None.
        Returns None if no persistency is configured. Thread-safe when a
        PersistencySaver is running: acquires the saver lock before saving
        (guards against the background save timer and concurrent ingest).
        """

        return PersistencyOp.__apply(
            instance=instance, path=path, storage_options=storage_options, op=save
        )

    @staticmethod
    def load(
        instance: object,
        path: str | bytes,
        storage_options: dict[str, Any] | None = None,
    ) -> None:
        """Restore this component's EventPersistency state.

        path may be an fsspec URI string or bytes returned by
        export_state(). No-op if no persistency is configured. Thread-safe
        when a PersistencySaver is running: acquires the saver lock before
        loading (guards against the background save timer).
        """

        PersistencyOp.__apply(
            instance=instance, path=path, storage_options=storage_options, op=load
        )
