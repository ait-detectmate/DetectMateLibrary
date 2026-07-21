from collections import deque
from typing import Sequence

from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common.detector import CoreDetectorConfig, CoreDetector
from detectmatelibrary.utils import persistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.schemas import ParserSchema, DetectorSchema

_SEQUENCE_SEPARATOR = "\x1f"

def _encode_sequence(sequence: Sequence[int]) -> str:
    return _SEQUENCE_SEPARATOR.join(str(event_id) for event_id in sequence)

class NewSequenceDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_sequence_detector"
    max_sequence_length: int = 5

class NewSequenceDetector(CoreDetector):
    def __init__(
            self,
            name: str = "NewSequenceDetector",
            config: NewSequenceDetectorConfig = NewSequenceDetectorConfig()
    ) -> None:
        if isinstance(config, dict):
            config = NewSequenceDetectorConfig.from_dict(config,name)