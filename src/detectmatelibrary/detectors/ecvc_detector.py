from typing import Any, Collection, List, Sequence
from typing_extensions import Self, override
import warnings

from detectmatelibrary.bases.base_detectors import CountVectorDetector, CountVectorDetectorConfig
from detectmatelibrary.bases.base_detectors.count_vector_detector import SessionWindows
from detectmatelibrary.utils.sequence_encoding import (
    build_count_vec,
    decode_count_vec,
)
from detectmatelibrary import schemas

from math import ceil
import numpy as np
from pydantic import Field


__all__ = ["ECVCDetector", "ECVCDetectorConfig", "ECVCOp", "SessionWindows"]


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


# method_type this detector used before it was corrected; still accepted.
_LEGACY_METHOD_TYPE = "ecvc_detector_detector"


class ECVCDetectorConfig(CountVectorDetectorConfig):
    method_type: str = Field(
        default="ecvc_detector", description="Indicates what type of method it is."
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


class ECVCDetector(CountVectorDetector):
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
        super().__init__(name=name, config=config)
        self.config: ECVCDetectorConfig

    @override
    def _sync_from_state(self) -> None:
        super()._sync_from_state()
        self.build_count_vec()  # no-op while no count vectors are stored

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
        super().post_train()

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema,
    ) -> bool:

        if self.count_vecs is None:
            return False

        events = self.window_events(input_)
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
