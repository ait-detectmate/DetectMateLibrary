from typing import Any, List

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


class SCVSDetectorConfig(CoreDetectorConfig):
    method_type: str = "scvs_detector"
    window_size: int = 10


class SCVSDetector(CoreDetector):
    def __init__(
        self,
        name: str = "SCVSDetector",
        config: SCVSDetectorConfig | dict[str, Any] = SCVSDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = SCVSDetectorConfig.from_dict(config, name)
        self.config: SCVSDetectorConfig

        super().__init__(
            name=name,
            buffer_mode=BufferMode.WINDOW,
            config=config,
            buffer_size=config.window_size
        )
        # ponytail: only events_seen is used here — count vectors carry no
        # variables. EventPersistency still requires an event_data_class.
        self.persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
        )
        self._register_persistency(self.persistency)  # restores state when auto_load
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        """Load state, then check it was trained at the configured window size.

        Unlike `auto_load`, this runs after construction, so the check in
        `__init__` has already passed and has to be redone here.
        """
        super().import_state(path, storage_options)
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)

    def train(self, input_: List[schemas.ParserSchema]) -> None:  # type: ignore
        self.persistency.ingest_event(
            event_id=encode_count_vec(self.config.window_size, build_count_vec(input_)),
            event_template=input_[-1]["template"],
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
