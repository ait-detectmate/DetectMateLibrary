from typing import Any, List

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

from pydantic import Field


class SCVSDetectorConfig(CoreDetectorConfig):
    method_type: str = Field(
        default="scvs_detector", description="Indicates what type of method it is."
    )
    window_size: int = Field(
        default=10,
        description="Length of the event-ID window a count vector is built over.",
    )


class SCVSDetector(CoreDetector, VariablesLogic):
    def __init__(
        self,
        name: str = "SCVSDetector",
        config: SCVSDetectorConfig | dict[str, Any] = SCVSDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = SCVSDetectorConfig.from_dict(config, name)
        self.config: SCVSDetectorConfig

        CoreDetector.__init__(
            self, name=name, buffer_mode=BufferMode.WINDOW, config=config, buffer_size=config.window_size
        )
        VariablesLogic.__init__(self, name=self.name)
        self._register_persistency(self.persistency)
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)

    def import_state(
        self, path: str | bytes, storage_options: dict[str, Any] | None = None
    ) -> None:
        CoreDetector.import_state(self, path, storage_options)
        warn_on_window_size_mismatch(self.name, self.persistency, self.config.window_size)

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

    def aggregate_strategy(self, components: set["SCVSDetector"]) -> None:  # type: ignore
        self.combine(components)  # type: ignore
