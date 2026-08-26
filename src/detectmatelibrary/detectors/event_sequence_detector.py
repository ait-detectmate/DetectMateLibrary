"""Detect EventID sequences that were not observed during training."""

from collections import deque
from typing import Any

from pydantic import Field, model_validator

from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common.detector import CoreDetectorConfig, CoreDetector
from detectmatelibrary.tools.logging import logger
from detectmatelibrary.utils import persistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.sequence_encoding import decode_sequence, encode_sequence
from detectmatelibrary.schemas import ParserSchema, DetectorSchema


class EventSequenceDetectorConfig(CoreDetectorConfig):
    """
    @param fixed_window_size length of the sliding EventID window. A window whose exact
           EventID sequence was not seen during training is reported as an anomaly. When
           set it overrides `min_window_size`/`max_window_size` and skips
           auto-configuration; auto-configuration writes its own choice here. While it is
           None the detector is unconfigured and neither trains nor alerts.
    @param min_window_size shortest window length tried during the auto-configuration
           phase. Only used while `fixed_window_size` is None.
    @param max_window_size longest window length tried during the auto-configuration
           phase. The longest length whose sequences are classified STABLE or STATIC wins.
    """
    method_type: str = "event_sequence_detector"
    min_window_size: int = Field(default=2, ge=1)
    max_window_size: int = Field(default=10, ge=1)
    fixed_window_size: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_window_range(self) -> "EventSequenceDetectorConfig":
        if self.max_window_size < self.min_window_size:
            raise ValueError("max_window_size must be >= min_window_size")
        return self


class EventSequenceDetector(CoreDetector):
    """Detect EventID sequences not encountered in training as anomalies."""

    def __init__(
            self,
            name: str = "EventSequenceDetector",
            config: EventSequenceDetectorConfig = EventSequenceDetectorConfig()
    ) -> None:
        if isinstance(config, dict):
            config = EventSequenceDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: EventSequenceDetectorConfig
        # CoreComponent.process() calls train() *and* run()->detect() for every
        # training event, so a single shared window would ingest each event twice.
        # maxlen is None while unconfigured, but nothing is appended in that state.
        self._train_window: deque[int] = deque(maxlen=self.config.fixed_window_size)
        self._detect_window: deque[int] = deque(maxlen=self.config.fixed_window_size)
        # ponytail: only events_seen is used here — sequences carry no variables.
        # EventPersistency still requires an event_data_class, and changing it would
        # change the on-disk format for no gain.
        self.persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
        )
        self._configure_windows: dict[int, deque[int]] = {}
        self.auto_conf_persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker
        )
        self._register_persistency(self.persistency)  # restores state when auto_load
        self._restored_length = self._adopt_restored_length()
        if not self.config.auto_config and self.config.fixed_window_size is None:
            logger.warning(
                f"[{self.name}] auto_config=False but no fixed_window_size was given. "
                "The detector stays unconfigured and will neither train nor alert."
            )

    def _set_window_length(self, length: int) -> None:
        """Set the window length and resize both sliding windows to match."""
        self.config.fixed_window_size = length
        self._train_window = deque(self._train_window, maxlen=length)
        self._detect_window = deque(self._detect_window, maxlen=length)

    def _adopt_restored_length(self) -> int | None:
        """Align `fixed_window_size` with restored state, if any.

        Sequences are stored as fixed-length n-grams, so a model trained at one
        length cannot be evaluated at another: every restored entry would miss and
        every detection would become a false positive. The persisted length
        therefore wins over the configured one.

        Returns the persisted length, or None when nothing was restored.
        """
        restored = self.persistency.get_events_seen()
        if not restored:
            return None
        length = len(decode_sequence(str(next(iter(restored)))))
        if length != self.config.fixed_window_size:
            logger.warning(
                f"[{self.name}] restored state holds sequences of length {length}, but "
                f"fixed_window_size is {self.config.fixed_window_size}. Using the "
                "persisted length — the restored model is only valid at that length."
            )
            self._set_window_length(length)
        return length

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        """Load state, then align the window length with what was restored.

        Unlike `auto_load`, this runs after construction, so the length check in
        `__init__` has already passed and has to be redone here.
        """
        super().import_state(path, storage_options)
        self._restored_length = self._adopt_restored_length()

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning EventID sequences from the input
        data.

        No-op while the window size is unconfigured.
        """
        if (length := self.config.fixed_window_size) is None:
            return
        self._train_window.append(input_["EventID"])
        if len(self._train_window) < length:
            return
        self.persistency.ingest_event(
            event_id=encode_sequence(self._train_window),
            event_template=input_["template"]
        )

    def detect(self, input_: ParserSchema, output_: DetectorSchema) -> bool:  # type: ignore
        """Report EventID windows that were not seen during training.

        A single novel event stays in the window for `fixed_window_size` steps
        and therefore yields that many alerts — each window is a distinct unseen
        sequence. No-op while the window size is unconfigured.
        """
        if (length := self.config.fixed_window_size) is None:
            return False
        self._detect_window.append(input_["EventID"])
        if len(self._detect_window) < length:
            return False

        if encode_sequence(self._detect_window) in self.persistency.get_events_seen():
            return False

        sequence = tuple(self._detect_window)
        output_["score"] = 1.0
        output_["description"] = f"{self.name} detects unknown EventID sequences as anomalies."
        output_["alertsObtain"].update({
            f"Sequence {sequence}": (
                f"EventID sequence of length {len(sequence)} ending at logID "
                f"{input_['logID']} was not seen during training."
            )
        })
        return True

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        """Feed the event into one sliding window per candidate length.

        Nothing to decide once `fixed_window_size` is set, whether by the user
        or by restored state.
        """
        if self.config.fixed_window_size is not None:
            return
        for length in range(self.config.min_window_size, self.config.max_window_size + 1):
            window = self._configure_windows.setdefault(length, deque(maxlen=length))
            window.append(input_["EventID"])
            if len(window) == length:
                self.auto_conf_persistency.ingest_event(
                    event_id=length,
                    event_template=input_["template"],
                    named_variables={"seq": tuple(window)},
                )

    def set_configuration(self) -> None:
        """Choose `fixed_window_size` from the configure-phase data.

        Each candidate length is scored by the stability of the
        sequences it produced; the longest STABLE or STATIC candidate
        wins. Candidates whose window never filled during the configure
        phase produced no data and are skipped. When nothing is stable
        an empty configuration is generated — this detector then holds
        no instance and stays silent, which beats alerting on every
        window at an arbitrary length.
        """
        if (fixed := self.config.fixed_window_size) is not None:
            reason = (
                "persisted state was restored" if self._restored_length is not None
                else "fixed_window_size is set"
            )
            logger.warning(
                f"[{self.name}] auto_config=True but {reason}. Keeping window size "
                f"{fixed}."
            )
            self._release_configure_state()
            return

        stable = []
        for length, event_tracker in self.auto_conf_persistency.get_events_data().items():
            tracker = event_tracker.get_data()["seq"]
            if len(tracker.change_series) < tracker.min_samples:
                continue
            if tracker.classify().type in ("STABLE", "STATIC"):
                stable.append(int(length))

        if not stable:
            logger.warning(
                f"[{self.name}] auto_config=True found no stable window size in "
                f"[{self.config.min_window_size}..{self.config.max_window_size}]. "
                "Generating an empty configuration — no instance of this detector is "
                "created and it will neither train nor alert."
            )
            old_persist = self.config.persist
            self.config = EventSequenceDetectorConfig.from_dict(
                generate_detector_config(
                    variable_selection={},
                    detector_name=self.name,
                    method_type=self.config.method_type,
                ),
                self.name,
            )
            self.config.persist = old_persist
            self._release_configure_state()
            return

        chosen = max(stable)
        logger.debug(
            f"[{self.name}] auto_config selected fixed_window_size={chosen} "
            f"from stable candidates {sorted(stable)}."
        )
        self._set_window_length(chosen)
        self._release_configure_state()

    def _release_configure_state(self) -> None:
        """Drop configure-phase state — nothing reads it after
        configuration."""
        self._configure_windows.clear()
        self.auto_conf_persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker
        )

    def reset_window(self) -> None:
        """Clear the training and detection windows."""
        self._train_window.clear()
        self._detect_window.clear()

    def get_known_sequences(self) -> set[tuple[int, ...]]:
        """Return the EventID sequences learned during training."""
        return {
            decode_sequence(str(encoded))
            for encoded in self.persistency.get_events_seen()
        }
