from detectmatelibrary.base_detectors import StabilityAutoConfigParams, TrackerDetector, TrackerDetectorConfig
from detectmatelibrary.common._config._compile import generate_events_config

from detectmatelibrary.tools.logging import logger
from detectmatelibrary.utils.sequence_encoding import decode_sequence, encode_sequence
from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode, DataBuffer

from detectmatelibrary.schemas import ParserSchema, DetectorSchema

from collections import deque

from typing_extensions import override
from pydantic import Field, model_validator


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


class SessionWindows:
    """The latest events of each session, oldest first."""

    def __init__(self) -> None:
        self.windows: dict[str, tuple[int, ...]] = {}

    def add(self, session: str, event: int, size: int) -> tuple[int, ...]:
        """Add `event` to `session` and return the session's last `size`
        events, which end at `event`; fewer at the session start."""
        window = (self.windows.get(session, ()) + (event,))[-size:]
        self.windows[session] = window
        return window


class EventSequenceDetectorConfig(TrackerDetectorConfig):
    method_type: str = Field(
        default="event_sequence_detector",
        description="Indicates what type of method it is.",
    )
    fixed_window_size: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Length of the sliding EventID window. A window whose exact "
            "EventID sequence was not seen during training is reported as an "
            "anomaly. When set it overrides the `auto_config_params` window "
            "range and skips auto-configuration; auto-configuration writes "
            "its own choice here. While it is None the detector is "
            "unconfigured and neither trains nor alerts."
        ),
    )

    session_variable: str | None = Field(
        default=None,
        description=(
            "Header variable that names the session of each event (HDFS: block_id). When set, "
            "an event's window holds the last fixed_window_size events of its own session, "
            "fewer at the session start, so windows never mix sessions and every event is "
            "checked."
        ),
    )

    auto_config_params: SequenceAutoConfigParams = SequenceAutoConfigParams()


class EventSequenceDetector(TrackerDetector):
    """Detect EventID sequences not encountered in training as anomalies."""

    def __init__(
        self,
        name: str = "EventSequenceDetector",
        config: EventSequenceDetectorConfig = EventSequenceDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = EventSequenceDetectorConfig.from_dict(config, name)
        self.config: EventSequenceDetectorConfig

        # Built before super().__init__(), whose _sync_from_state resizes them.
        self._train_window: deque[int] = deque(maxlen=config.fixed_window_size)
        self._detect_window: deque[int] = deque(maxlen=config.fixed_window_size)
        self._configure_windows: dict[int, deque[int]] = {}
        self._restored_length: int | None = None
        # With sessions, train() and configure() keep their own windows: train() also gets the
        # configure records, replayed after the configure phase. detect() does not get them, so
        # its windows are built where every record passes once, the buffer.
        self._train_sessions = SessionWindows()
        self._configure_sessions = SessionWindows()
        self._detect_sessions = SessionWindows()
        self._session_window: tuple[int, ...] = ()

        super().__init__(
            name=name,
            config=config,
            buffer_mode=BufferMode.NO_BUF,
            stability_params=config.auto_config_params,
        )
        if config.session_variable is not None:
            self.args_buffer = ArgsBuffer(BufferMode.NO_BUF, process_function=self._add_to_session)
            self.data_buffer = DataBuffer(self.args_buffer)

        if not self.config.auto_config and self.config.fixed_window_size is None:
            logger.warning(
                f"[{self.name}] auto_config=False but no fixed_window_size was given. "
                "The detector stays unconfigured and will neither train nor alert."
            )

    def _session(self, input_: ParserSchema) -> str:
        session = input_["headerVariables"].get(self.config.session_variable)
        if session is None:
            raise ValueError(
                f"[{self.name}] log has no header variable {self.config.session_variable!r}"
            )
        return str(session)

    def _add_to_session(self, input_: ParserSchema) -> ParserSchema:
        """Buffer hook: extend the detection window of the record's session.

        Before configuration the length is still open, so the longest
        candidate is kept; detect() cuts the window to the chosen length.
        """
        size = self.config.fixed_window_size or self.config.auto_config_params.max_window_size
        self._session_window = self._detect_sessions.add(self._session(input_), input_["eventID"], size)
        return input_

    def _set_window_length(self, length: int) -> None:
        """Set the window length and resize both sliding windows to match."""
        self.config.fixed_window_size = length
        self._train_window = deque(self._train_window, maxlen=length)
        self._detect_window = deque(self._detect_window, maxlen=length)

    def _adopt_restored_length(self) -> None:
        """Align `fixed_window_size` with restored state, if any.

        Sequences are stored as fixed-length n-grams, so a model trained at one
        length cannot be evaluated at another: every restored entry would miss and
        every detection would become a false positive. The persisted length
        therefore wins over the configured one. With sessions, the windows at a
        session start are shorter, so the length is that of the longest sequence.
        """
        restored = self.persistency.get_events_seen()
        if not restored:
            self._restored_length = None
        else:
            length = max(len(decode_sequence(str(encoded))) for encoded in restored)
            if length != self.config.fixed_window_size:
                logger.warning(
                    f"[{self.name}] restored state holds sequences of length {length}, but "
                    f"fixed_window_size is {self.config.fixed_window_size}. Using the "
                    "persisted length — the restored model is only valid at that length."
                )
                self._set_window_length(length)
            self._restored_length = length

    @override
    def _sync_from_state(self) -> None:
        self._adopt_restored_length()

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning EventID sequences from the input
        data.

        No-op while the window size is unconfigured.
        """
        if (length := self.config.fixed_window_size) is None:
            return
        if self.config.session_variable is not None:
            window = self._train_sessions.add(self._session(input_), input_["eventID"], length)
        else:
            self._train_window.append(input_["eventID"])
            if len(self._train_window) < length:
                return
            window = tuple(self._train_window)
        self.persistency.ingest_event(
            event_id=encode_sequence(window),
            event_template=input_["template"],
        )

    def detect(self, input_: ParserSchema, output_: DetectorSchema) -> bool:  # type: ignore
        """Report EventID windows that were not seen during training.

        A single novel event stays in the window for `fixed_window_size` steps
        and therefore yields that many alerts — each window is a distinct unseen
        sequence. No-op while the window size is unconfigured. With sessions the
        window is the one the buffer built for this record, so call process().
        """
        if (length := self.config.fixed_window_size) is None:
            return False
        if self.config.session_variable is not None:
            sequence = self._session_window[-length:]
        else:
            self._detect_window.append(input_["eventID"])
            if len(self._detect_window) < length:
                return False
            sequence = tuple(self._detect_window)

        if encode_sequence(sequence) in self.persistency.get_events_seen():
            return False

        output_["score"] = 1.0
        output_["description"] = (
            f"{self.name} detects unknown EventID sequences as anomalies."
        )
        output_["alertDetails"].update(
            {
                f"Sequence {sequence}": (
                    f"EventID sequence of length {len(sequence)} ending at logID "
                    f"{input_['logID']} was not seen during training."
                )
            }
        )
        return True

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        """Feed the event into one sliding window per candidate length.

        Nothing to decide once `fixed_window_size` is set, whether by the user
        or by restored state. With sessions each length gets the window that
        detection would use at that length, so session starts count too.
        """
        if self.config.fixed_window_size is not None:
            return
        auto = self.config.auto_config_params
        if self.config.session_variable is not None:
            latest = self._configure_sessions.add(
                self._session(input_), input_["eventID"], auto.max_window_size
            )
        for length in range(auto.min_window_size, auto.max_window_size + 1):
            if self.config.session_variable is not None:
                sequence = latest[-length:]
            else:
                window = self._configure_windows.setdefault(length, deque(maxlen=length))
                window.append(input_["eventID"])
                if len(window) < length:
                    continue
                sequence = tuple(window)
            self.auto_conf_persistency.ingest_event(
                event_id=length,
                event_template=input_["template"],
                named_variables={"seq": sequence},
                timestamp=self._timestamps.read(input_),
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
                "persisted state was restored"
                if self._restored_length is not None
                else "fixed_window_size is set"
            )
            logger.warning(
                f"[{self.name}] auto_config=True but {reason}. Keeping window size "
                f"{fixed}."
            )
            self._release_configure_state()
            return

        stable = []
        for (
            length,
            event_tracker,
        ) in self.auto_conf_persistency.get_events_data().items():
            tracker = event_tracker.get_data()["seq"]
            if len(tracker.change_series) < tracker.min_samples:  # type: ignore
                continue
            if tracker.classify().type in ("STABLE", "STATIC"):
                stable.append(int(length))

        if not stable:
            auto = self.config.auto_config_params
            logger.warning(
                f"[{self.name}] auto_config=True found no stable window size in "
                f"[{auto.min_window_size}..{auto.max_window_size}]. "
                "Generating an empty configuration — no instance of this detector is "
                "created and it will neither train nor alert."
            )
            self.config.events = generate_events_config({}, self.name)
            self.config.auto_config = False
            self._release_configure_state()
            return

        chosen = max(stable)
        logger.debug(
            f"[{self.name}] auto_config selected fixed_window_size={chosen} "
            f"from stable candidates {sorted(stable)}."
        )
        self.config.events = generate_events_config({}, self.name)
        self._set_window_length(chosen)
        self.config.auto_config = False
        self._release_configure_state()

    def _release_configure_state(self) -> None:
        """Drop configure-phase state — nothing reads it after
        configuration."""
        self._configure_windows.clear()
        self._configure_sessions = SessionWindows()
        self.auto_conf_persistency = self._new_store()

    def reset_window(self) -> None:
        """Clear the training and detection windows."""
        self._train_window.clear()
        self._detect_window.clear()
        self._train_sessions = SessionWindows()
        self._detect_sessions = SessionWindows()
        self._session_window = ()

    def get_known_sequences(self) -> set[tuple[int, ...]]:
        """Return the EventID sequences learned during training."""
        return {
            decode_sequence(str(encoded))
            for encoded in self.persistency.get_events_seen()
        }
