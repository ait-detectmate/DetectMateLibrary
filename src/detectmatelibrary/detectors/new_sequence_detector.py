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
    max_sequence_length: int = 3
    sequence_length_candidates: list[int] = [2, 3, 4, 5, 6, 8, 10]
    # TODO: min and max sequence length would probably be better, min would be 2 and max 10 for example


class NewSequenceDetector(CoreDetector):
    def __init__(
            self,
            name: str = "NewSequenceDetector",
            config: NewSequenceDetectorConfig = NewSequenceDetectorConfig()
    ) -> None:
        if isinstance(config, dict):
            config = NewSequenceDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: NewSequenceDetectorConfig
        self._window: deque[int] = deque(maxlen=self.config.max_sequence_length)
        self.persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
        )
        self._configure_windows: dict[int, deque[int]] = {
            w: deque(maxlen=w) for w in self.config.sequence_length_candidates
        }
        self.auto_conf_persistency = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker
        )
        self._register_persistency(self.persistency)

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning EventID sequences from the input
        data."""
        self._window.append(input_["EventID"])
        if len(self._window) < self.config.max_sequence_length:
            return
        self.persistency.ingest_event(
            event_id=_encode_sequence(self._window),
            event_template=input_["template"]
        )

    def detect(self, input_: ParserSchema, output_: DetectorSchema) -> bool:  # type: ignore
        self._window.append(input_["EventID"])
        if len(self._window) < self.config.max_sequence_length:
            return False

        if _encode_sequence(self._window) not in self.persistency.get_events_seen():
            output_["score"] = 1.0
            output_["description"] = f"{self.name} detects unknown EventID sequences as anomalies."
            output_["alertsObtain"].update({
                f"Sequence {tuple(self._window)}": f"Unknown sequence: {tuple(self._window)}"
            })
            return True
        return False

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        for w in self.config.sequence_length_candidates:
            self._configure_windows[w].append(input_["EventID"])
            if len(self._configure_windows[w]) == w:
                self.auto_conf_persistency.ingest_event(
                    event_id=w,
                    event_template=input_["template"],
                    named_variables={"seq": tuple(self._configure_windows[w])},
                )

    def set_configuration(self) -> None:
        stable = []
        for w in self.config.sequence_length_candidates:
            tracker = self.auto_conf_persistency.get_events_data()[w].get_data()["seq"]
            if tracker.classify().type in ("STABLE", "STATIC"):
                stable.append(w)

        chosen = max(stable) if stable else min(self.config.sequence_length_candidates)

        old_persist = self.config.persist
        config_dict = generate_detector_config(
            variable_selection={},
            detector_name=self.name,
            method_type=self.config.method_type,
            max_sequence_length=chosen,
        )
        self.config = NewSequenceDetectorConfig.from_dict(config_dict, self.name)
        self.config.persist = old_persist
        self._window = deque(self._window, maxlen=self.config.max_sequence_length)

    def reset_window(self) -> None:
        self._window.clear()

    def get_known_sequences(self) -> set[tuple[str, ...]]:
        return {
            tuple(str(encoded).split(_SEQUENCE_SEPARATOR))
            for encoded in self.persistency.get_events_seen()
        }
