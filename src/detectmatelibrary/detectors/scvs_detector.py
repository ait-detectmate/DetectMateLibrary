from typing import Any, List

from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary import schemas


def build_count_vec(input_: List[schemas.ParserSchema]) -> tuple[int, ...]:
    sequence, n = [0], 0
    for in_ in input_:
        event = in_["EventID"]
        if n < event:
            for _ in range(n, event + 1):
                sequence.append(0)
            n = event
        sequence[event] += 1

    return tuple(sequence)


class SequenceSetDetectorConfig(CoreDetectorConfig):
    method_type: str = "sequence_set_detector_detector"
    window_size: int = 10


class SequenceSetDetector(CoreDetector):
    def __init__(
        self,
        name: str = "SequenceSetDetector",
        config: SequenceSetDetectorConfig | dict[str, Any] = SequenceSetDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = SequenceSetDetectorConfig.from_dict(config, name)
        self.config: SequenceSetDetectorConfig

        super().__init__(
            name=name,
            buffer_mode=BufferMode.WINDOW,
            config=config,
            buffer_size=config.window_size
        )
        self.train_seqs: set[tuple[int, ...]] = set()

    def train(self, input_: List[schemas.ParserSchema]) -> None:  # type: ignore
        self.train_seqs.add(build_count_vec(input_))

    def detect(
        self, input_: List[schemas.ParserSchema], output_: schemas.DetectorSchema,  # type: ignore
    ) -> bool:

        if build_count_vec(input_) not in self.train_seqs:
            output_["score"] = 1.
            output_["description"] = "Sequence not found"
            return True

        return False
