from detectmatelibrary.utils.persistency.data_structures.trackers.stability import ClassificationMethods
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.time_format_handler import TimeFormatHandler

from detectmatelibrary.subcommon._stability import StabilityAutoConfigParams

from detectmatelibrary.tools.logging import logger
from detectmatelibrary.schemas import ParserSchema

from typing import Any, Dict, Optional
import polars as pl
import io


class VaribaleHooks:
    """Hooks use to define the dfferent behaviours in th next subclasses."""
    def __init__(self, name: str, config_vars: StabilityAutoConfigParams) -> None:
        self.name = name
        self._warned_bad_timestamp: bool = False
        self.config_vars = config_vars

    def _with_classification_kwargs(
        self, kwargs: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:

        if self.config_vars.classification == ClassificationMethods():
            return kwargs
        return {**(kwargs or {}), "classification": self.config_vars.classification.model_dump()}

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return None

    def _auto_conf_kwargs(self) -> Optional[Dict[str, Any]]:
        return self._event_data_kwargs()


class VariablesLogic(VaribaleHooks):
    """Variables logic combining the hooks and persistency class."""
    def __init__(
        self,
        name: str,
        allow_fed: bool = False,
        _time_handler: TimeFormatHandler = TimeFormatHandler(),
        config_vars: StabilityAutoConfigParams = StabilityAutoConfigParams(),
    ) -> None:

        super().__init__(name=name, config_vars=config_vars)
        self._time_handler = _time_handler
        self.persistency = EventPersistency(
            event_data_kwargs=self._event_data_kwargs(), do_slow_per=allow_fed
        )
        self.auto_conf_persistency = EventPersistency(
            event_data_kwargs=self._with_classification_kwargs(self._auto_conf_kwargs()),
            do_slow_per=False,
        )

    def _warn_time_fallback_once(self, reason: str) -> None:
        """Log the first time-dependent misconfiguration, then stay quiet.

        A bad config would otherwise emit one warning per record, so the
        flag latches after the first message.
        """
        if self._warned_bad_timestamp:
            return
        self._warned_bad_timestamp = True
        logger.warning(
            "%s: %s; falling back to the index axis for stability classification.",
            self.name, reason,
        )

    def _timestamp(self, input_: ParserSchema) -> float | None:
        """Resolve the record's event time, or None if no enabled
        classification method reads the time axis."""
        if not self.config_vars.classification.needs_timestamps:
            return None

        if not self.config_vars.timestamp_variable:
            self._warn_time_fallback_once(
                "a time-axis classification method is enabled "
                "but timestamp_variable is not set"
            )
            return None

        raw = input_["logFormatVariables"].get(self.config_vars.timestamp_variable)
        ts = self._time_handler.parse_timestamp(str(raw or ""), self.config_vars.timestamp_format)
        if ts == "0":
            self._warn_time_fallback_once(
                f"timestamp_variable {self.config_vars.timestamp_variable!r} is missing or "
                f"unparseable (got {raw!r})"
            )
            return None

        return float(ts)

    def _ingest(
        self, input_: ParserSchema, variables: Dict[str, Any], event_id: Any
    ) -> None:
        self.persistency.ingest_event(
            event_id=event_id,
            event_template=input_["template"],
            named_variables=variables
        )

    def combine(self, components: set["VariablesLogic"]) -> None:
        for component in components:
            if self != component:
                self.persistency.combine(component.persistency)

        for component in components:
            component.persistency = self.persistency

    def persistency2binary(self) -> bytes:
        return self.persistency.event_struct.get_data().serialize()  # type: ignore

    def binary2persistency(self, binary: bytes) -> None:
        self.persistency.event_struct.overwrite_slow(
            pl.DataFrame.deserialize(io.BytesIO(binary))
        )
        self.persistency.combine(self.persistency)  # Fill fast persistency with slow

    def clean_persistency(self) -> None:
        self.persistency.event_struct.slow_persistency.clean()
