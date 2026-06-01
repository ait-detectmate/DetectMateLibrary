from typing import Any, cast

from detectmatelibrary.common._config._compile import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.common.detector import (
    CoreDetectorConfig,
    CoreDetector,
    get_configured_variables,
    get_global_variables,
    validate_config_coverage,
)
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
)
from detectmatelibrary.utils.persistency.event_persistency import EventPersistency
from detectmatelibrary.utils.data_buffer import BufferMode
from detectmatelibrary.schemas import ParserSchema, DetectorSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID, DEFAULT_FREQUENCIES
from typing_extensions import override
from tools.logging import logger


_DEFAULT_FREQ: dict[str, dict[str, int]] | None = None
_DEFAULT_TOTAL_FREQ: dict[str, int] | None = None


def _default_freq_tables() -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    """Lazily parse DEFAULT_FREQUENCIES into string-keyed lookup tables."""
    global _DEFAULT_FREQ, _DEFAULT_TOTAL_FREQ
    if _DEFAULT_FREQ is None or _DEFAULT_TOTAL_FREQ is None:
        freq: dict[str, dict[str, int]] = {}
        total: dict[str, int] = {}
        for first_char_raw, second_list in DEFAULT_FREQUENCIES:
            first_char = cast(str, first_char_raw)
            row: dict[str, int] = {}
            row_total = 0
            for second_char_raw, count_raw in second_list:
                second_char = cast(str, second_char_raw)
                count = cast(int, count_raw)
                row[second_char] = count
                row_total += count
            freq[first_char] = row
            total[first_char] = row_total
        _DEFAULT_FREQ = freq
        _DEFAULT_TOTAL_FREQ = total
    return _DEFAULT_FREQ, _DEFAULT_TOTAL_FREQ


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
        """Train the detector by updating per-variable bigram frequencies."""
        configured_variables = get_configured_variables(input_, self.config.events)
        current_event_id = input_["EventID"]
        known_events = cast(
            dict[int | str, EventStabilityTracker], self.persistency.get_events_data()
        )

        pre_unique = self._snapshot_unique_sets(
            known_events.get(current_event_id), configured_variables
        )
        self.persistency.ingest_event(
            event_id=current_event_id,
            event_template=input_["template"],
            named_variables=configured_variables,
        )
        if configured_variables:
            known_events = cast(
                dict[int | str, EventStabilityTracker], self.persistency.get_events_data()
            )
            self.train_helper(configured_variables, current_event_id, known_events, pre_unique)

        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                pre_unique_global = self._snapshot_unique_sets(
                    known_events.get(GLOBAL_EVENT_ID), global_vars
                )
                self.persistency.ingest_event(
                    event_id=GLOBAL_EVENT_ID,
                    event_template=input_["template"],
                    named_variables=global_vars,
                )
                known_events = cast(
                    dict[int | str, EventStabilityTracker], self.persistency.get_events_data()
                )
                self.train_helper(global_vars, GLOBAL_EVENT_ID, known_events, pre_unique_global)

    @staticmethod
    def _snapshot_unique_sets(
        event_tracker: "EventStabilityTracker | None",
        variables: "dict[str, Any]",
    ) -> "dict[str, set[Any]]":
        """Capture pre-ingest unique_set membership per variable.

        Used so train_helper's skip_repetitions check sees the
        unique_set as it was *before* the current value was ingested.
        Variables without a prior tracker get an empty set, which
        naturally means skip_repetitions never skips on first
        occurrence.
        """
        if event_tracker is None:
            return {var: set() for var in variables}
        existing = cast(dict[str, SingleStabilityTracker], event_tracker.get_data())
        result: dict[str, set[Any]] = {}
        for var in variables:
            tracker = existing.get(var)
            result[var] = set(tracker.unique_set) if tracker is not None else set()
        return result

    def train_helper(
        self,
        variables: "dict[str, Any]",
        event_id: "int | str",
        known_events: "dict[int | str, EventStabilityTracker]",
        pre_unique: "dict[str, set[Any]]",
    ) -> None:
        var_trackers = cast(
            dict[str, SingleStabilityTracker], known_events[event_id].get_data()
        )
        for var_name, value in variables.items():
            if value is None:
                continue
            if self.config.skip_repetitions and value in pre_unique.get(var_name, set()):
                continue
            tracker = var_trackers[var_name]
            freq = tracker.extra_state.setdefault("freq", {})
            total_freq = tracker.extra_state.setdefault("total_freq", {})
            for i in range(-1, len(value)):
                first = -1 if i == -1 else value[i]
                second = -1 if i == len(value) - 1 else value[i + 1]
                row = freq.setdefault(first, {})
                row[second] = row.get(second, 0) + 1
                total_freq[first] = total_freq.get(first, 0) + 1

    def detect(
        self, input_: ParserSchema, output_: DetectorSchema  # type: ignore
    ) -> bool:
        """Detect bigram-frequency anomalies in the input data."""
        alerts: dict[str, str] = {}
        configured_variables = get_configured_variables(input_, self.config.events)
        overall_score = 0.0
        current_event_id = input_["EventID"]
        known_events = cast(
            dict[int | str, EventStabilityTracker], self.persistency.get_events_data()
        )
        if current_event_id in known_events:
            overall_score = self.detect_helper(
                alerts, configured_variables, current_event_id, known_events, overall_score
            )
        if self.config.global_instances and GLOBAL_EVENT_ID in known_events:
            global_vars = get_global_variables(input_, self.config.global_instances)
            overall_score = self.detect_helper(
                alerts, global_vars, GLOBAL_EVENT_ID, known_events, overall_score
            )
        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = f"{self.name} anomalies in the bigram frequencies."
            output_["alertsObtain"].update(alerts)
            return True
        return False

    def detect_helper(
        self,
        alerts: dict[str, str],
        variables: dict[str, Any],
        event_id: "int | str",
        known_events: "dict[int | str, EventStabilityTracker]",
        overall_score: float,
    ) -> float:
        anomaly = False
        default_freq, default_total = (
            _default_freq_tables() if self.config.default_freqs else ({}, {})
        )
        var_trackers = cast(
            dict[str, SingleStabilityTracker], known_events[event_id].get_data()
        )
        for var_name, single_tracker in var_trackers.items():
            value: Any = variables.get(var_name)
            if value is None:
                continue
            freq: dict[Any, dict[Any, int]] = single_tracker.extra_state.get("freq", {})
            total_freq: dict[Any, int] = single_tracker.extra_state.get("total_freq", {})
            probs: list[float] = []
            for i in range(-1, len(value)):
                first: Any = -1 if i == -1 else value[i]
                second: Any = -1 if i == len(value) - 1 else value[i + 1]
                prob = 0.0
                if first in freq and second in freq[first] and total_freq.get(first, 0) > 0:
                    prob = freq[first][second] / total_freq[first]
                elif self.config.default_freqs:
                    if (first in default_freq and second in default_freq[first]
                            and default_total.get(first, 0) > 0):
                        prob = default_freq[first][second] / default_total[first]
                probs.append(prob)
            if not probs:
                continue
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
