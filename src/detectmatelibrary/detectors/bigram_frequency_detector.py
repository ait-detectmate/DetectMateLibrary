from typing import Any

from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.common.detector import (
    CoreDetectorConfig,
    CoreDetector,
    get_configured_variables,
    get_global_variables,
    validate_config_coverage,
)
from detectmatelibrary.utils.persistency.event_data_structures.base import EventDataStructure
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID
from typing_extensions import override
from tools.logging import logger


class BigramFrequencyDetectorConfig(CoreDetectorConfig):
    # documentation see: https://github.com/ernstleierzopf/logdata-anomaly-miner/blob/main/source
    # /root/usr/lib/logdata-anomaly-miner/aminer/analysis/EntropyDetector.py
    method_type: str = "bigram_frequency_detector"
    prob_thresh: float = 0.05
    default_freqs: bool = False
    skip_repetitions: bool = False

    use_stable_vars: bool = True
    use_static_vars: bool = True


class BigramFrequencyDetector(CoreDetector):
    """Detect bigram-frequency-based anomalies in log data."""

    def __init__(
        self,
        name: str = "BigramFrequencyDetector",
        config: BigramFrequencyDetectorConfig = BigramFrequencyDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = BigramFrequencyDetectorConfig.from_dict(config, name)

        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: BigramFrequencyDetectorConfig  # type narrowing for IDE
        self.persistency = EventPersistency(
            event_data_class=EventStabilityTracker,
        )
        # auto config checks if individual variables are stable to select combos from
        self.auto_conf_persistency = EventPersistency(
            event_data_class=EventStabilityTracker
        )
        self._register_persistency(self.persistency)

    def train(self, input_: ParserSchema) -> None:  # type: ignore
        """Train the detector by learning values from the input data."""
        configured_variables = get_configured_variables(input_, self.config.events)
        current_event_id = input_["EventID"]
        known_events = self.persistency.get_events_data()
        add_all = current_event_id not in known_events
        if current_event_id in known_events:
            self.train_helper(add_all, configured_variables, current_event_id, known_events)
        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                add_all = GLOBAL_EVENT_ID not in known_events
                if not add_all:
                    self.train_helper(add_all, global_vars, GLOBAL_EVENT_ID, known_events)
                self.persistency.ingest_event(
                    event_id=GLOBAL_EVENT_ID,
                    event_template=input_["template"],
                    named_variables=global_vars
                )
                if add_all:
                    self.train_helper(add_all, global_vars, GLOBAL_EVENT_ID, known_events)
        self.persistency.ingest_event(
            event_id=current_event_id,
            event_template=input_["template"],
            named_variables=configured_variables
        )

    def train_helper(self, add_all: bool, variables: dict[str, Any], event_id: str,
                     known_events: dict[int | str, EventDataStructure]) -> None:
        for var_name, multi_tracker in known_events[event_id].get_data().items():
            value: Any = variables.get(var_name)
            if value is None:
                continue
            if self.config.skip_repetitions:
                # Do not consider repeating values multiple times for extending frequency table to
                # avoid distortions.
                if not add_all and value in multi_tracker.unique_set:
                    continue
            for i in range(-1, len(value)):
                first_char = -1
                if i != -1:
                    first_char = value[i]
                second_char = -1
                if i != len(value) - 1:
                    second_char = value[i + 1]
                if first_char in self.freq:  # type: ignore[attr-defined]
                    self.total_freq[first_char] += 1  # type: ignore[attr-defined]
                    if second_char in self.freq[first_char]:  # type: ignore[attr-defined]
                        self.freq[first_char][second_char] += 1  # type: ignore[attr-defined]
                    else:
                        self.freq[first_char][second_char] = 1  # type: ignore[attr-defined]
                else:
                    self.total_freq[first_char] = 1  # type: ignore[attr-defined]
                    self.freq[first_char] = {}  # type: ignore[attr-defined]
                    self.freq[first_char][second_char] = 1  # type: ignore[attr-defined]

    def detect(
        self, input_:  ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        """Detect new values in the input data."""
        alerts: dict[str, str] = {}
        configured_variables = get_configured_variables(input_, self.config.events)
        overall_score = 0.0
        current_event_id = input_["EventID"]
        known_events = self.persistency.get_events_data()
        if current_event_id in known_events:
            overall_score = self.detect_helper(alerts, configured_variables, current_event_id, known_events,
                                               overall_score)
        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = get_global_variables(input_, self.config.global_instances)
            overall_score = self.detect_helper(
                alerts, global_vars, GLOBAL_EVENT_ID, known_events, overall_score)
        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = f"{self.name} anomalies in the bigram frequencies."
            output_["alertsObtain"].update(alerts)
            return True
        return False

    def detect_helper(self, alerts: dict[str, str], variables: dict[str, Any], event_id: str,
                      known_events: dict[int | str, EventDataStructure], overall_score: float) -> float:
        anomaly = False
        for var_name, multi_tracker in known_events[event_id].get_data().items():
            value: Any = variables.get(var_name)
            probs = []
            # Iterate over all characters (+ virtual characters before and after value)
            # and check occurrence frequencies of ith and (i+1)th character
            for i in range(-1, len(value)):
                # Use -1 as placeholder for character before first actual character of value
                first_char = -1
                if i != -1:
                    first_char = value[i]
                # Use -1 as placeholder for character after last actual character of value
                second_char = -1
                if i != len(value) - 1:
                    second_char = value[i + 1]
                prob = 0.0
                freq = self.freq  # type: ignore[attr-defined]
                total_freq = self.total_freq  # type: ignore[attr-defined]
                if first_char in freq and second_char in freq[first_char]:
                    prob = freq[first_char][second_char] / total_freq[first_char]
                probs.append(prob)
            critical_val = sum(probs) / len(probs)
            if critical_val < self.config.prob_thresh:
                k = f"EventID {event_id} - {var_name}"
                if event_id == GLOBAL_EVENT_ID:
                    k = f"Global - {var_name}"
                alerts[k] = (
                    f"Bigram frequency anomaly with value {value}, critical_val {critical_val} and "
                    f"threshold {self.config.prob_thresh}."
                )
                anomaly = True
        if anomaly:
            overall_score += 1.0
        return overall_score

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        self.auto_conf_persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            named_variables=input_["logFormatVariables"],
        )

    @override
    def post_train(self) -> None:
        if not self.config.auto_config:
            validate_config_coverage(self.name, self.config.events, self.persistency)

    def set_configuration(self) -> None:
        variables = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable = []
            if self.config.use_stable_vars:
                stable = tracker.get_features_by_classification("STABLE")  # type: ignore
            static = []
            if self.config.use_static_vars:
                static = tracker.get_features_by_classification("STATIC")  # type: ignore
            vars_ = stable + static
            if len(vars_) > 0:
                variables[event_id] = vars_
        config_dict = generate_detector_config(
            variable_selection=variables,
            detector_name=self.name,
            method_type=self.config.method_type,
        )
        old_persist = self.config.persist
        self.config = BigramFrequencyDetectorConfig.from_dict(config_dict, self.name)
        self.config.persist = old_persist
        events = self.config.events
        if isinstance(events, EventsConfig) and not events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variables were found in configure-phase data. "
                "The detector will produce no alerts."
            )
