from detectmatelibrary.common._config import generate_detector_config
from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary.common.variable_detector import VariableDetector, VariableDetectorConfig
from detectmatelibrary.common.detector import get_configured_variables

from detectmatelibrary.utils import persistency
from detectmatelibrary.utils.persistency.event_data_structures.trackers.stability.stability_tracker import (
    SingleStabilityTracker,
)

from detectmatelibrary.schemas import ParserSchema

from typing import Any, Dict, Optional, Sequence, Tuple, cast
from itertools import combinations

from detectmatelibrary.tools.logging import logger


def get_combo(variables: Dict[str, Any]) -> Dict[Tuple[str, ...], Tuple[Any, ...]]:
    """Get a single combination of all variables as a key-value pair."""
    return {tuple(variables.keys()): tuple(variables.values())}


def _combine(iterable: Sequence[str], max_combo_length: int = 2) -> list[Tuple[str, ...]]:
    """Get all possible combinations of an iterable."""
    combos: list[Tuple[str, ...]] = []
    for i in range(2, min(len(iterable), max_combo_length, 5) + 1):
        combos.extend(list(combinations(iterable, i)))
    return combos


def get_all_possible_combos(
    variables: Dict[str, Any], max_combo_length: int = 2
) -> Dict[Tuple[str, ...], Tuple[Any, ...]]:
    """Get all combinations of specified variables as key-value pairs."""
    combo_dict = {}
    for combo in _combine(list(variables.keys()), max_combo_length):
        combo_dict[tuple(combo)] = tuple(variables[var] for var in combo)
    return combo_dict


class NewValueComboDetectorConfig(VariableDetectorConfig):
    method_type: str = "new_value_combo_detector"

    max_combo_size: int = 3
    use_static_vars: bool = False


class NewValueComboDetector(VariableDetector):
    def __init__(
        self,
        name: str = "NewValueComboDetector",
        config: NewValueComboDetectorConfig = NewValueComboDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = NewValueComboDetectorConfig.from_dict(config, name)
        super().__init__(name=name, config=config)
        self.config: NewValueComboDetectorConfig  # type narrowing for IDE
        # second-pass persistency to learn stability of variable combinations
        self.auto_conf_persistency_combos = persistency.EventPersistency(
            event_data_class=persistency.EventStabilityTracker,
            event_data_kwargs=self._with_segmentation(
                {"converter_function": get_all_possible_combos}
            ),
        )
        self.inputs: list[ParserSchema] = []

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return {"converter_function": get_combo}

    def _auto_conf_kwargs(self) -> Optional[Dict[str, Any]]:
        return None  # first-pass auto-config tracks individual variables

    def _prepare_variables(self, variables: Dict[str, Any], stage: str) -> Dict[str, Any]:
        if stage == "detection":
            return cast(Dict[str, Any], get_combo(variables))
        return variables

    def _check_variable(
        self, tracker: SingleStabilityTracker, value: Any, key: Any
    ) -> Optional[str]:
        if value not in tracker.unique_set:
            return f"Unknown value combination: {value}"
        return None

    def _description(self) -> str:
        return (
            f"{self.name} detects value combinations not encountered "
            "in training as anomalies."
        )

    def configure(self, input_: ParserSchema) -> None:  # type: ignore
        # store inputs to re-ingest after the first configuration pass
        self.inputs.append(input_)
        super().configure(input_)

    def set_configuration(self, max_combo_size: int | None = None) -> None:
        """Set configuration based on the stability of variable combinations.

        1. Analyze individual-variable stability to identify stable variables.
        2. Generate an initial config with combos of stable variables.
        3. Re-ingest all events to learn the stability of those combos (testing
           every possible combo up front would explode combinatorially).
        """
        old_persist = self.config.persist
        segmentation_fields = {
            "stability_segmentation": self.config.stability_segmentation,
            "timestamp_variable": self.config.timestamp_variable,
            "timestamp_format": self.config.timestamp_format,
        }

        def restore_segmentation_fields() -> None:
            """Carry the segmentation settings across a config reassignment.

            generate_detector_config only emits method_type / auto_config /
            params / events, so every ``from_dict`` below resets these to their
            defaults. The re-ingest loop calls ``_timestamp()`` under the pass-1
            config, so restoring only at the end would leave the combo trackers
            timestamp-less.
            """
            for field, value in segmentation_fields.items():
                setattr(self.config, field, value)

        # pass 1: stable individual variables -> combos
        variable_combos = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_features_by_classification("STABLE")  # type: ignore
            if len(stable_vars) > 1:
                variable_combos[event_id] = stable_vars
        config_dict = generate_detector_config(
            variable_selection=variable_combos,
            detector_name=self.name,
            method_type=self.config.method_type,
            max_combo_size=max_combo_size or self.config.max_combo_size,
        )
        self.config = NewValueComboDetectorConfig.from_dict(config_dict, self.name)
        restore_segmentation_fields()

        # re-ingest all inputs to learn combos under the new configuration
        for input_ in self.inputs:
            configured_variables = get_configured_variables(input_, self.config.events)
            self.auto_conf_persistency_combos.ingest_event(
                event_id=input_["EventID"],
                event_template=input_["template"],
                named_variables=configured_variables,
                timestamp=self._timestamp(input_),
            )

        # pass 2: stable/static combos -> final config
        combo_selection = {}
        for event_id, tracker in self.auto_conf_persistency_combos.get_events_data().items():
            stable_combos = (
                tracker.get_features_by_classification("STABLE")  # type: ignore
                if self.config.use_stable_vars
                else []
            )
            static_combos = (
                tracker.get_features_by_classification("STATIC")  # type: ignore
                if self.config.use_static_vars
                else []
            )
            combos = stable_combos + static_combos
            if combos:
                combo_selection[event_id] = combos
        config_dict = generate_detector_config(
            variable_selection=combo_selection,
            detector_name=self.name,
            method_type=self.config.method_type,
            max_combo_size=max_combo_size or self.config.max_combo_size,
        )
        self.config = NewValueComboDetectorConfig.from_dict(config_dict, self.name)
        self.config.persist = old_persist
        restore_segmentation_fields()
        events = self.config.events
        if isinstance(events, EventsConfig) and not events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variable combinations were found in configure-phase data. "
                "The detector will produce no alerts."
            )
