from typing import Any, List

from detectmatelibrary.subcommon import TrackerDetector, TrackerDetectorConfig

from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.utils.sequence_encoding import (
    build_count_vec,
    decode_count_vec,
    encode_count_vec,
    warn_on_window_size_mismatch,
)
from detectmatelibrary import schemas

from pydantic import Field
from typing_extensions import override


class SCVSDetectorConfig(TrackerDetectorConfig):
    method_type: str = Field(
        default="scvs_detector", description="Indicates what type of method it is."
    )
    window_size: int = Field(
        default=10,
        description="Length of the event-ID window a count vector is built over.",
    )


class SCVSDetector(TrackerDetector):
    def __init__(
        self,
        name: str = "SCVSDetector",
        config: SCVSDetectorConfig | dict[str, Any] = SCVSDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = SCVSDetectorConfig.from_dict(config, name)
        self.config: SCVSDetectorConfig

        super().__init__(
            name=name, config=config, buffer_mode=BufferMode.WINDOW, buffer_size=config.window_size
        )

    @override
    def _sync_from_state(self) -> None:
        warn_on_window_size_mismatch(self.name, self.persistency.get_events_seen(), self.config.window_size)

    def train(self, input_: List[schemas.ParserSchema]) -> None:  # type: ignore
        self._ingest(
            event_id=encode_count_vec(self.config.window_size, build_count_vec(input_)),
            input_=input_[-1],
            variables={}
        )

    def detect(
        self, input_: List[schemas.ParserSchema], output_: schemas.DetectorSchema,  # type: ignore
    ) -> bool:

        key = encode_count_vec(self.config.window_size, build_count_vec(input_))
        if key not in self.persistency.get_events_seen():
            output_["score"] = 1.
            output_["description"] = "Count vector not found"
            return True

        return False

    def get_known_count_vecs(self) -> set[tuple[int, ...]]:
        """Return the count vectors learned during training."""
        return {
            decode_count_vec(str(encoded))[1]
            for encoded in self.persistency.get_events_seen()
        }
