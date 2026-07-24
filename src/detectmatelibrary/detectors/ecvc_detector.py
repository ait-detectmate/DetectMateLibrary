from typing import Any, List

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary import schemas

from scipy.stats import mode
from math import ceil
import numpy as np


class ECVCOp:
    @staticmethod
    def build_count_vec(input_: List[schemas.ParserSchema]) -> tuple[int, ...]:
        sequence, n = [0], 0
        for in_ in input_:
            event = in_["EventID"]
            if n < event:
                for _ in range(n, event):
                    sequence.append(0)
                n = event
            sequence[event] += 1

        return tuple(sequence)

    @staticmethod
    def build_one_vec(input_: List[schemas.ParserSchema], n: int) -> np.ndarray:
        events = [in_["EventID"] for in_ in input_]
        arr = np.zeros(n if n > (m := max(events) + 1) else m)

        for e in events:
            arr[e] += 1

        return arr

    @staticmethod
    def init_count_matrix(seqs: set[tuple[int, ...]]) -> np.ndarray:
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
        elif method == "mode":
            return float(mode([ECVCOp.calculate_score(y, matrix=matrix) for y in y_s]).mode)
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
        self.train_seqs: set[tuple[int, ...]] = set()
        self.count_vecs: np.ndarray | None = None
        self.threshold: float = 0

    def train(self, input_: List[schemas.ParserSchema]) -> None:  # type: ignore
        self.train_seqs.add(ECVCOp.build_count_vec(input_))

    def post_train(self) -> None:
        train_idx = ceil(len(self.train_seqs) * (1 - self.config.validation_per))
        np.random.seed(self.config.seed)
        matrix = ECVCOp.init_count_matrix(self.train_seqs)[np.random.permutation(len(self.train_seqs))]

        self.count_vecs, val = matrix[:train_idx], matrix[train_idx:]
        if len(val) > 0:
            self.threshold = ECVCOp.threshold_cal(
                y_s=val, matrix=self.count_vecs, method=self.config.threshold_method
            )
        self.train_seqs = set()

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
