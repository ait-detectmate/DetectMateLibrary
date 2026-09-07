from typing import Any, Collection, List

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.utils import persistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.sequence_encoding import (
    build_count_vec,
    decode_count_vec,
    encode_count_vec,
    warn_on_window_size_mismatch,
)
from detectmatelibrary import schemas

from math import ceil
import numpy as np


class ECVCOp:
    build_count_vec = staticmethod(build_count_vec)

    @staticmethod
    def build_one_vec(input_: List[schemas.ParserSchema], n: int) -> np.ndarray:
        events = [in_["EventID"] for in_ in input_]
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
        pad = np.zeros((matrix.shape[0], y.shape[0] - matrix.shape[1]))
        matrix_ = np.concat([matrix, pad], axis=1)

        score = np.inf
        for m in matrix_:
            dif = np.sum(np.abs(m - y))
            div = np.sum(np.max(np.concat([m[np.newaxis], y[np.newaxis]]).T, axis=1))
            score = score if score < (s := (dif / div)) else s

        return float(score)

    @staticmethod
    def threshold_cal(y_s: np.ndarray, matrix: np.ndarray, method: str) -> float:
        if method == "mean":
            return float(np.mean([ECVCOp.calculate_score(y, matrix=matrix) for y in y_s]))
        elif method == "default":
            return 0.0

        raise Exception("Method not supported")


class ECVCDetectorConfig(CoreDetectorConfig):
    method_type: str = "ecvc_detector_detector"
    window_size: int = 10
    validation_per: float = 0.2
    seed: int = 0
    threshold_method: str = "mean"


class ECVCDetector(CoreDetector):
    def __init__(
        self,
        name: str = "ECVCDetector",
        config: ECVCDetectorConfig | dict[str, Any] = ECVCDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = ECVCDetectorConfig.from_dict(config, name)
        self.config: ECVCDetectorConfig

        super().__init__(
            name=name,
            buffer_mode=BufferMode.WINDOW,
            config=config,
            buffer_size=config.window_size
        )
        self.count_vecs: np.ndarray | None = None
        self.threshold: float = 0
        # ponytail: only events_seen is used here — count vectors carry no
        # variables. EventPersistency still requires an event_data_class.
        self.persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
        )
        self._register_persistency(self.persistency)  # restores state when auto_load
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)
        self._derive()  # no-op unless auto_load restored count vectors

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        """Load state, then rebuild the matrix and threshold from it.

        Unlike `auto_load`, this runs after construction, so the derivation in
        `__init__` has already run against an empty store and has to be redone.
        """
        super().import_state(path, storage_options)
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)
        self._derive()

    def train(self, input_: List[schemas.ParserSchema]) -> None:  # type: ignore
        self.persistency.ingest_event(
            event_id=encode_count_vec(self.config.window_size, ECVCOp.build_count_vec(input_)),
            event_template=input_[-1]["template"],
        )

    def _derive(self) -> None:
        """Build the count vector matrix and threshold from the learned
        vectors.

        The vectors are sorted first: restored keys are strings, whose set
        iteration order is hash-randomized per process, and the seeded shuffle
        below splits train from validation by that order. Sorting makes a
        restored model identical to a freshly trained one.
        """
        seqs = sorted(
            decode_count_vec(str(encoded))[1]
            for encoded in self.persistency.get_events_seen()
        )
        if not seqs:
            return

        train_idx = ceil(len(seqs) * (1 - self.config.validation_per))
        np.random.seed(self.config.seed)
        matrix = ECVCOp.init_count_matrix(seqs)[np.random.permutation(len(seqs))]

        self.count_vecs, val = matrix[:train_idx], matrix[train_idx:]
        if len(val) > 0:
            self.threshold = ECVCOp.threshold_cal(
                y_s=val, matrix=self.count_vecs, method=self.config.threshold_method
            )

    def post_train(self) -> None:
        self._derive()

    def detect(
        self, input_: List[schemas.ParserSchema], output_: schemas.DetectorSchema,  # type: ignore
    ) -> bool:

        if self.count_vecs is None:
            return False

        score = ECVCOp.calculate_score(ECVCOp.build_one_vec(
            input_, self.count_vecs.shape[1]), matrix=self.count_vecs
        )
        if score > self.threshold:
            output_["score"] = score
            output_["description"] = "ECVC found an anominal sequence"
            return True

        return False
