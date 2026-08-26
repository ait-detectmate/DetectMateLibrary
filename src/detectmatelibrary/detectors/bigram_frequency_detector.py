from typing import Any, Dict, Optional, cast

from detectmatelibrary.common.variable_detector import VariableDetector, VariableDetectorConfig
from detectmatelibrary.common.variable_detector import get_global_variables
from detectmatelibrary.common._config._compile import get_configured_variables
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    EventStabilityTracker,
    SingleStabilityTracker,
)
from detectmatelibrary.schemas import ParserSchema
from detectmatelibrary.constants import GLOBAL_EVENT_ID, DEFAULT_FREQUENCIES


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


class BigramFrequencyDetectorConfig(VariableDetectorConfig):
    """
    @param prob_thresh limit for the average probability of character pairs for which anomalies are reported.
    @param default_freqs initializes the probabilities with default values from
           https://github.com/markbaggett/freq.
    @param skip_repetitions boolean that determines whether only distinct values are used for character pair
           counting. This counteracts the problem of imbalanced word frequencies that distort the frequency
           table generated in a single run.
    """
    method_type: str = "bigram_frequency_detector"
    prob_thresh: float = 0.05
    default_freqs: bool = False
    skip_repetitions: bool = True


class BigramFrequencyDetector(VariableDetector):
    """Detect bigram-frequency-based anomalies in log data."""

    def __init__(
        self,
        name: str = "BigramFrequencyDetector",
        config: BigramFrequencyDetectorConfig = BigramFrequencyDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = BigramFrequencyDetectorConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self.config: BigramFrequencyDetectorConfig  # type narrowing for IDE

    def add_value(self, tracker: SingleStabilityTracker, value: Any) -> None:
        """Add a new value to the tracker (bigram-frequency semantics)."""
        change = False
        default_freq, default_total = (_default_freq_tables() if self.config.default_freqs else ({}, {}))
        freq: dict[Any, dict[Any, int]] = tracker.extra_state.get("freq", {})
        total_freq: dict[Any, int] = tracker.extra_state.get("total_freq", {})
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
        if probs:
            critical_val = sum(probs) / len(probs)
            change = critical_val > self.config.prob_thresh or any(x == 0.0 for x in probs)

        if self.config.skip_repetitions and value in tracker.unique_set:
            change = False
        else:
            for i in range(-1, len(value)):
                first = -1 if i == -1 else value[i]
                second = -1 if i == len(value) - 1 else value[i + 1]
                row = freq.setdefault(first, {})
                row[second] = row.get(second, 0) + 1
                total_freq[first] = total_freq.get(first, 0) + 1
        tracker.unique_set.add(value)
        tracker.change_series.append(change)

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return self._stability_kwargs()

    def _description(self) -> str:
        return f"{self.name} anomalies in the bigram frequencies."

    # ---- training (overrides base: needs pre-ingest snapshot + freq update) --

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
            known_events = cast(dict[int | str, EventStabilityTracker], self.persistency.get_events_data())
            self.train_helper(configured_variables, current_event_id, known_events, pre_unique)

        if self.config.global_instances:
            global_vars = get_global_variables(input_, self.config.global_instances)
            if global_vars:
                pre_unique_global = self._snapshot_unique_sets(known_events.get(GLOBAL_EVENT_ID), global_vars)
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

    # ---- detection (overrides _check_event: event-level +1 scoring) ----------

    def _check_event(
        self,
        alerts: Dict[str, str],
        event_id: Any,
        event_tracker: EventStabilityTracker,
        variables: Dict[str, Any],
        is_global: bool,
    ) -> float:
        anomaly = False
        default_freq, default_total = (_default_freq_tables() if self.config.default_freqs else ({}, {}))
        var_trackers = cast(dict[str, SingleStabilityTracker], event_tracker.get_data())
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
                alerts[self._alert_key(event_id, var_name, is_global)] = (
                    f"Bigram frequency anomaly with value {value}, critical_val {critical_val} and "
                    f"threshold {self.config.prob_thresh}."
                )
                anomaly = True
        return 1.0 if anomaly else 0.0
