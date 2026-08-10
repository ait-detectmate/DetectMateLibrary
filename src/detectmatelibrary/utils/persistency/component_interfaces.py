from pydantic import BaseModel, ConfigDict, Field

import os

from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.schemas import ParserSchema
from detectmatelibrary.tools.logging import logger

from .event_persistency import EventPersistency
from .persistency_saver import load, save

from typing import Any, Callable, Dict, Protocol


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


# Detector Core Component ##################################################################

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


def get_configured_variables(
        input_: ParserSchema,
        log_variables: EventsConfig | dict[str, Any],
) -> Dict[str, Any]:
    """Extract variables from input based on what's defined in the config.

    Args:
        input_: Parser schema containing variables and logFormatVariables
        log_variables: Config specifying which variables to extract per EventID

    Returns:
        Dict mapping variable names to their values from the input
    """
    event_id = input_["EventID"]
    result: Dict[str, Any] = {}

    # Get the config for this event
    event_config = log_variables[event_id] if event_id in log_variables else None
    if event_config is None:
        return result

    # Extract template variables by position
    if hasattr(event_config, "variables"):
        for pos, var in event_config.variables.items():
            if isinstance(pos, int) and pos < len(input_["variables"]):
                result[var.name] = input_["variables"][pos]

    # Extract header/log format variables by name
    if hasattr(event_config, "header_variables"):
        for name in event_config.header_variables:
            if name in input_["logFormatVariables"]:
                result[name] = input_["logFormatVariables"][name]

    return result


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
