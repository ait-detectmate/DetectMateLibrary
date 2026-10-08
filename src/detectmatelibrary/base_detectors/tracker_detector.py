from detectmatelibrary.common._core_op._fed_component import FedOperations
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.base_detectors._persist import PersistConfig, load_state, save_state, start_saver
from detectmatelibrary.base_detectors._stability import StabilityAutoConfigParams, TimestampReader

from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.persistency.data_structures.trackers.stability import ClassificationMethods
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.persistency.persistency_saver import PersistencySaver
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

from detectmatelibrary.schemas import ParserSchema

from typing_extensions import Self, override
from typing import Any, Dict, Optional, cast
from pydantic import Field
import polars as pl
import io


class TrackerDetectorConfig(CoreDetectorConfig):
    method_type: str = Field(default="tracker_detector", description="<$IGNORE$>")
    persist: PersistConfig | None = Field(
        default=None,
        description=(
            "Periodic state saving (path, interval_seconds, events_until_save, auto_load, "
            "storage_options). None disables it. See the Persistency page."
        ),
    )
    allow_fed: bool = Field(
        default=False,
        description=(
            "Allow to do the federation"
        ),
    )


class TrackerDetector(CoreDetector):
    """Base for detectors whose model lives in EventPersistency stores.

    Owns the stores (`persistency`, `auto_conf_persistency`), their periodic
    saving (`persist`), `export_state`/`import_state` and federation.
    Subclasses ingest with `_ingest`, read the stores' methods, build any
    extra store with `_new_store`, and rebuild derived fields in
    `_sync_from_state`. They never import `utils.persistency`.
    """

    # One handler for every tracker detector, as the old shared default was.
    _time_handler: TimeFormatHandler = TimeFormatHandler()

    def __init__(
        self,
        name: str,
        config: TrackerDetectorConfig,
        buffer_mode: BufferMode = BufferMode.NO_BUF,
        buffer_size: Optional[int] = None,
        stability_params: StabilityAutoConfigParams = StabilityAutoConfigParams(),
    ) -> None:
        CoreDetector.__init__(
            self, name=name, buffer_mode=buffer_mode, buffer_size=buffer_size, config=config
        )
        self.config: TrackerDetectorConfig
        self.config_vars = stability_params
        self._timestamps = TimestampReader(self.name, stability_params, self._time_handler)
        self.persistency = EventPersistency(
            event_data_kwargs=self._event_data_kwargs(), do_slow_per=config.allow_fed
        )
        self.auto_conf_persistency = self._new_store(self._auto_conf_kwargs(), classified=True)
        # may restore saved state (auto_load), so the sync comes after it
        self.saver: PersistencySaver | None = start_saver(self.name, config.persist, self.persistency)
        self._sync_from_state()

    # ---- stores -----------------------------------------------------------

    def _with_classification_kwargs(
        self, kwargs: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Add the configured classification methods to tracker kwargs, unless
        they are the defaults."""
        if self.config_vars.classification == ClassificationMethods():
            return kwargs
        return {**(kwargs or {}), "classification": self.config_vars.classification.model_dump()}

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        """Tracker kwargs for `persistency`, the store detection reads."""
        return None

    def _auto_conf_kwargs(self) -> Optional[Dict[str, Any]]:
        """Tracker kwargs for `auto_conf_persistency`, before the
        classification methods are added."""
        return self._event_data_kwargs()

    def _new_store(
        self, event_data_kwargs: Optional[Dict[str, Any]] = None, *, classified: bool = False
    ) -> EventPersistency:
        """Build an extra store, e.g. for a second configure pass.

        With `classified`, its trackers use the configured classification
        methods. Extra stores are neither saved nor federated.
        """
        if classified:
            event_data_kwargs = self._with_classification_kwargs(event_data_kwargs)
        return EventPersistency(event_data_kwargs=event_data_kwargs, do_slow_per=False)

    def _ingest(
        self, input_: ParserSchema, variables: Dict[str, Any], event_id: Any
    ) -> None:
        """Add one event and its variables to `persistency`."""
        self.persistency.ingest_event(
            event_id=event_id,
            event_template=input_["template"],
            named_variables=variables
        )

    def _sync_from_state(self) -> None:
        """Bring fields derived from the stores back in line with them.

        Called whenever the stores change without training: at the end of
        `__init__` (after a possible `auto_load`), after `import_state`, on
        the detector `from_binary` returns, and on every component after
        `aggregate_strategy`. The default does nothing.

        Ordering rule: the first call runs inside `TrackerDetector.__init__`,
        so everything an override reads or writes must exist before
        `super().__init__()` returns -- as a class attribute, or assigned
        before the `super().__init__()` call.
        """

    # ---- state I/O ----------------------------------------------------------

    @override
    def export_state(
        self,
        path: str | None = None,
        storage_options: dict[str, Any] | None = None,
    ) -> bytes | None:
        """Save the state of `persistency`.

        When path is None, returns the state as bytes (zip archive).
        When path is given, writes to that fsspec URI and returns None.
        Holds the saver lock while saving, so a running PersistencySaver
        cannot save at the same time.
        """
        return save_state(self.persistency, self.saver, path, storage_options)

    @override
    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        """Restore the state of `persistency`, then `_sync_from_state`.

        path may be an fsspec URI string or bytes returned by
        export_state(). Holds the saver lock while loading.
        """
        load_state(self.persistency, self.saver, path, storage_options)
        self._sync_from_state()

    @override
    def __exit__(self, *_: Any) -> None:
        """Stop the periodic saver, which saves one last time."""
        if self.saver is not None:
            self.saver.stop()

    # ---- federation ---------------------------------------------------------

    @override
    def to_binary(self) -> bytes:
        return self.persistency.event_struct.get_data().serialize()  # type: ignore

    @override
    def from_binary(self, binary: bytes) -> Self:
        """A new detector with this name and config, holding the state in
        `binary`."""
        other = type(self)(name=self.name, config=self.config)
        other.persistency.event_struct.overwrite_slow(
            pl.DataFrame.deserialize(io.BytesIO(binary))
        )
        other.persistency.combine(other.persistency)  # Fill fast persistency with slow
        other._sync_from_state()
        return other

    @override
    def aggregate_strategy(self, components: set[FedOperations]) -> None:
        """Merge every component's store into this one, share the result, then
        `_sync_from_state` each component."""
        trackers = cast(set["TrackerDetector"], components)
        for component in trackers:
            if component is not self:
                self.persistency.combine(component.persistency)

        for component in trackers | {self}:
            component.persistency = self.persistency
            component._sync_from_state()

    @override
    def finalize_federation(self) -> None:
        """Delete the slow-persistency table when the store has one.

        Stores are built with a slow table only when `allow_fed` was set at
        construction.
        """
        if self.persistency.event_struct.do_slow:
            self.persistency.event_struct.slow_persistency.clean()
