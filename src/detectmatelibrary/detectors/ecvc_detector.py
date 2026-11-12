from typing import Any, Collection, List, Sequence
from typing_extensions import Self, override
import warnings

from detectmatelibrary.base_detectors import TrackerDetector, TrackerDetectorConfig

from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode, DataBuffer
from detectmatelibrary.utils.sequence_encoding import (
    build_count_vec,
    count_events,
    decode_count_vec,
    encode_count_vec,
    warn_on_window_size_mismatch,
)
from detectmatelibrary import schemas

from math import ceil
import numpy as np
from pydantic import Field


class ECVCOp:
    build_count_vec = staticmethod(build_count_vec)

    @staticmethod
    def build_one_vec(input_: List[schemas.ParserSchema], n: int) -> np.ndarray:
        return ECVCOp.events_vec([in_["eventID"] for in_ in input_], n)

    @staticmethod
    def events_vec(events: Sequence[int], n: int) -> np.ndarray:
        """Count vector of `events`, at least `n` long."""
        arr = np.zeros(n if n > (m := max(events) + 1) else m)

        for e in events:
            arr[e] += 1

        return arr

    @staticmethod
    def init_count_matrix(seqs: Collection[tuple[int, ...]]) -> np.ndarray:
        m, n = len(seqs), max([len(s) for s in seqs])
        matrix = np.zeros((m, n))

        for i, seq in enumerate(seqs):
            for j, c in enumerate(seq):
                matrix[i, j] = c

        return matrix

    @staticmethod
    def calculate_score(y: np.ndarray, matrix: np.ndarray) -> float:
        """Lowest of sum |m - y| / sum max(m, y) over the rows m of matrix."""
        if y.shape[0] != matrix.shape[1]:
            matrix = np.pad(matrix, ((0, 0), (0, y.shape[0] - matrix.shape[1])))

        dif = np.abs(matrix - y).sum(axis=1)
        div = np.maximum(matrix, y).sum(axis=1)
        return float(np.min(dif / div, initial=np.inf))

    @staticmethod
    def vec_key(vec: np.ndarray) -> bytes:
        """Hashable key of a count vector, blind to trailing zeros."""
        return bytes(np.trim_zeros(vec, "b").tobytes())

    @staticmethod
    def threshold_cal(y_s: np.ndarray, matrix: np.ndarray, method: str) -> float:
        if method == "mean":
            return float(np.mean([ECVCOp.calculate_score(y, matrix=matrix) for y in y_s]))
        elif method == "default":
            return 0.0

        raise Exception("Method not supported")


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


# method_type this detector used before it was corrected; still accepted.
_LEGACY_METHOD_TYPE = "ecvc_detector_detector"


class ECVCDetectorConfig(TrackerDetectorConfig):
    method_type: str = Field(
        default="ecvc_detector", description="Indicates what type of method it is."
    )
    window_size: int = Field(
        default=10,
        description="Length of the event-ID window a count vector is built over.",
    )
    validation_per: float = Field(
        default=0.2,
        description=(
            "Fraction of the learned count vectors held out as a validation "
            "split and used to derive the anomaly threshold. Detection still "
            "matches them: a window seen in training never alerts."
        ),
    )
    seed: int = Field(
        default=0,
        description="Random seed used to shuffle count vectors into train/validation splits.",
    )
    threshold_method: str = Field(
        default="mean",
        description=(
            "Method used to derive the anomaly threshold from the validation "
            "split: 'mean' averages the distance scores, 'default' uses a "
            "fixed threshold of 0."
        ),
    )
    session_variable: str | None = Field(
        default=None,
        description=(
            "Header variable that names the session of each event (HDFS: block_id). When set, "
            "an event's window holds the last window_size events of its own session, fewer at "
            "the session start, so windows never mix sessions and every event is checked."
        ),
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any], method_id: str) -> Self:
        method = data.get(cls().component_type, {}).get(method_id, {})
        if method.get("method_type") == _LEGACY_METHOD_TYPE:
            warnings.warn(
                f"method_type '{_LEGACY_METHOD_TYPE}' is deprecated, use 'ecvc_detector'.",
                DeprecationWarning,
                stacklevel=2,
            )
            data = {**data, cls().component_type: {
                **data[cls().component_type],
                method_id: {**method, "method_type": "ecvc_detector"},
            }}
        return super().from_dict(data, method_id)


class ECVCDetector(TrackerDetector):
    # Class-level defaults: _sync_from_state runs inside TrackerDetector.__init__.
    count_vecs: np.ndarray | None = None
    known_vecs: frozenset[bytes] = frozenset()  # vec_key of each row of count_vecs
    threshold: float = 0.0

    def __init__(
        self,
        name: str = "ECVCDetector",
        config: ECVCDetectorConfig | dict[str, Any] = ECVCDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = ECVCDetectorConfig.from_dict(config, name)
        self.config: ECVCDetectorConfig

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

    @override
    def _sync_from_state(self) -> None:
        warn_on_window_size_mismatch(self.name, self.persistency.get_events_seen(), self.config.window_size)
        self.build_count_vec()  # no-op while no count vectors are stored

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

    def build_count_vec(self) -> None:
        seqs = sorted(
            decode_count_vec(str(encoded))[1]
            for encoded in self.persistency.get_events_seen()
        )
        if not seqs:
            return

        train_idx = ceil(len(seqs) * (1 - self.config.validation_per))
        np.random.seed(self.config.seed)
        matrix = ECVCOp.init_count_matrix(seqs)[np.random.permutation(len(seqs))]

        train, val = matrix[:train_idx], matrix[train_idx:]
        if len(val) > 0:
            self.threshold = ECVCOp.threshold_cal(
                y_s=val, matrix=train, method=self.config.threshold_method
            )
        # The validation split only sets the threshold: detection matches every learned
        # vector, so a window seen in training never alerts.
        self.count_vecs = matrix
        self.known_vecs = frozenset(ECVCOp.vec_key(vec) for vec in self.count_vecs)

    def post_train(self) -> None:
        self.build_count_vec()
        self.train_windows = SessionWindows(self.config.window_size)

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema,
    ) -> bool:

        if self.count_vecs is None:
            return False

        events = [in_["eventID"] for in_ in input_] if isinstance(input_, list) else self.window
        y = ECVCOp.events_vec(events, self.count_vecs.shape[1])
        # A window equal to a learned vector scores 0, which never exceeds the threshold.
        if ECVCOp.vec_key(y) in self.known_vecs:
            return False

        score = ECVCOp.calculate_score(y, matrix=self.count_vecs)
        if score > self.threshold:
            output_["score"] = score
            output_["description"] = "ECVC found an anominal sequence"
            return True

        return False
