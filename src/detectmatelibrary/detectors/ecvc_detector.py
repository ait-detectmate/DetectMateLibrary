from typing import Any, Collection, List

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.common._other_op._variable_hooks import VariablesLogic

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
from pydantic import Field


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
    method_type: str = Field(
        default="ecvc_detector_detector", description="Indicates what type of method it is."
    )
    window_size: int = Field(
        default=10,
        description="Length of the event-ID window a count vector is built over.",
    )
    validation_per: float = Field(
        default=0.2,
        description=(
            "Fraction of the learned count vectors held out as a validation "
            "split and used to derive the anomaly threshold."
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


class ECVCDetector(CoreDetector, VariablesLogic):
    def __init__(
        self,
        name: str = "ECVCDetector",
        config: ECVCDetectorConfig | dict[str, Any] = ECVCDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = ECVCDetectorConfig.from_dict(config, name)
        self.config: ECVCDetectorConfig

        CoreDetector.__init__(
            self, name=name, buffer_mode=BufferMode.WINDOW, config=config, buffer_size=config.window_size
        )
        VariablesLogic.__init__(self, name=self.name)
        self._register_persistency(self.persistency)
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)

        self.count_vecs: np.ndarray | None = None
        self.threshold: float = 0
        self.build_count_vec()  # no-op unless auto_load restored count vectors

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        CoreDetector.import_state(self, path, storage_options)
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)
        self.build_count_vec()

    def train(self, input_: List[schemas.ParserSchema]) -> None:  # type: ignore
        self._ingest(
            event_id=encode_count_vec(self.config.window_size, ECVCOp.build_count_vec(input_)),
            input_=input_[-1],
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

        self.count_vecs, val = matrix[:train_idx], matrix[train_idx:]
        if len(val) > 0:
            self.threshold = ECVCOp.threshold_cal(
                y_s=val, matrix=self.count_vecs, method=self.config.threshold_method
            )

    def post_train(self) -> None:
        self.build_count_vec()

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

    def aggregate_strategy(self, components: set["ECVCDetector"]) -> None:  # type: ignore
        self.combine(components)  # type: ignore

        self.build_count_vec()
        for component in components:
            component.build_count_vec()
