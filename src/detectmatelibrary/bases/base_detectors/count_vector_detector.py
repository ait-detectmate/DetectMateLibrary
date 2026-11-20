from typing import List, Sequence
from typing_extensions import override

from detectmatelibrary import schemas
from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode, DataBuffer
from detectmatelibrary.utils.sequence_encoding import (
    count_events,
    decode_count_vec,
    encode_count_vec,
    warn_on_window_size_mismatch,
)

from pydantic import Field

from .tracker_detector import TrackerDetector, TrackerDetectorConfig


class SessionWindows:
    """The window ending at the latest event of each session: its last `size`
    events, fewer at the session start."""

    def __init__(self, size: int) -> None:
        self.size = size
        self.windows: dict[str, tuple[int, ...]] = {}

    def add(self, session: str, event: int) -> tuple[int, ...]:
        """Add ``event`` to ``session`` and return the session's window ending
        at it."""
        window = (self.windows.get(session, ()) + (event,))[-self.size:]
        self.windows[session] = window
        return window


class CountVectorDetectorConfig(TrackerDetectorConfig):
    window_size: int = Field(
        default=10,
        description="Length of the event-ID window a count vector is built over.",
    )
    session_variable: str | None = Field(
        default=None,
        description=(
            "Header variable that names the session of each event (HDFS: block_id). When set, "
            "an event's window holds the last window_size events of its own session, fewer at "
            "the session start, so windows never mix sessions and every event is checked."
        ),
    )


class CountVectorDetector(TrackerDetector):
    """Base of the detectors that learn the count vectors of event-ID
    windows."""

    def __init__(self, name: str, config: CountVectorDetectorConfig) -> None:
        self.config: CountVectorDetectorConfig

        by_session = config.session_variable is not None
        super().__init__(
            name=name,
            config=config,
            buffer_mode=BufferMode.NO_BUF if by_session else BufferMode.WINDOW,
            buffer_size=None if by_session else config.window_size,
        )
        # With sessions, train() keeps its own windows: it also gets the configure records,
        # replayed after the configure phase. detect() does not get them, so its windows are
        # built where every record passes once, the buffer.
        self.train_windows = SessionWindows(config.window_size)
        self.detect_windows = SessionWindows(config.window_size)
        self.window: tuple[int, ...] = ()
        if by_session:
            self.args_buffer = ArgsBuffer(BufferMode.NO_BUF, process_function=self._add_to_session)
            self.data_buffer = DataBuffer(self.args_buffer)

    def _session(self, input_: schemas.ParserSchema) -> str:
        session = input_["headerVariables"].get(self.config.session_variable)
        if session is None:
            raise ValueError(f"<<{self.name}>> log has no header variable {self.config.session_variable!r}")
        return str(session)

    def _add_to_session(self, input_: schemas.ParserSchema) -> schemas.ParserSchema:
        self.window = self.detect_windows.add(self._session(input_), input_["eventID"])
        return input_

    def window_events(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> Sequence[int]:
        """Event IDs of the window of ``input_``."""
        if isinstance(input_, list):
            return [in_["eventID"] for in_ in input_]
        return self.window

    @override
    def _sync_from_state(self) -> None:
        warn_on_window_size_mismatch(self.name, self.persistency.get_events_seen(), self.config.window_size)

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        if isinstance(input_, list):
            events: Sequence[int] = [in_["eventID"] for in_ in input_]
            last = input_[-1]
        else:
            events, last = self.train_windows.add(self._session(input_), input_["eventID"]), input_
        self._ingest(
            event_id=encode_count_vec(self.config.window_size, count_events(events)),
            input_=last,
            variables={}
        )

    def post_train(self) -> None:
        self.train_windows = SessionWindows(self.config.window_size)

    def get_known_count_vecs(self) -> set[tuple[int, ...]]:
        """Return the count vectors learned during training."""
        return {
            decode_count_vec(str(encoded))[1]
            for encoded in self.persistency.get_events_seen()
        }
