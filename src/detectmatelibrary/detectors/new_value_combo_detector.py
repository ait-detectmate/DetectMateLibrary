from detectmatelibrary.common._config import generate_events_config
from detectmatelibrary.common._config._compile import (
    get_configured_variables,
    get_instance_variables,
)
from detectmatelibrary.common._core_op._train_buffer import TrainBuffer
from detectmatelibrary.base_detectors import (
    SingleStabilityTracker,
    VariableAutoConfigParams,
    VariableDetector,
    VariableDetectorConfig,
)

from detectmatelibrary.schemas import ParserSchema

from typing import Any, Dict, List, Optional, Sequence, Tuple, cast
from itertools import combinations
import re

from pydantic import Field

from detectmatelibrary.tools.logging import logger


_POSITIONAL_VARIABLE = re.compile(r"^var_(\d+)$")


def _variable_order(name: str) -> Tuple[int, int, str]:
    """Sort key: template variables by position, then header variables by
    name."""
    match = _POSITIONAL_VARIABLE.match(name)
    return (0, int(match.group(1)), "") if match else (1, 0, name)


def _combo_order(combo: Tuple[str, ...]) -> Tuple[int, List[Tuple[int, int, str]]]:
    """Sort key: smaller combinations first, then by their variables."""
    return len(combo), [_variable_order(name) for name in combo]


def get_combo(variables: Dict[str, Any]) -> Dict[Tuple[str, ...], Tuple[Any, ...]]:
    """Get a single combination of all variables as a key-value pair."""
    return {tuple(variables.keys()): tuple(variables.values())}


def _combine(
    iterable: Sequence[str], max_combo_length: int = 2
) -> list[Tuple[str, ...]]:
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


class ComboAutoConfigParams(VariableAutoConfigParams):
    # Combo-detector default, unchanged from the flat field it replaces.
    use_static_vars: bool = Field(
        default=False,
        description="Monitor the variables the configure phase classifies as STATIC (a single value).",
    )
    # Read only while auto_config is True: detection reads the combos the phase
    # wrote into `events`, never this.
    max_combo_size: int = Field(
        default=3,
        description=(
            "Largest number of variables the configure phase combines into one monitored combination."
        ),
    )


class NewValueComboDetectorConfig(VariableDetectorConfig):
    method_type: str = Field(
        default="new_value_combo_detector",
        description="Indicates what type of method it is.",
    )

    auto_config_params: ComboAutoConfigParams = ComboAutoConfigParams()


class NewValueComboDetector(VariableDetector):
    def __init__(
        self,
        name: str = "NewValueComboDetector",
        config: NewValueComboDetectorConfig | dict[str, Any] = NewValueComboDetectorConfig(),
    ) -> None:
        if isinstance(config, dict):
            config = NewValueComboDetectorConfig.from_dict(config, name)
        super().__init__(name=name, config=config)
        self.config: NewValueComboDetectorConfig  # type narrowing for IDE
        # second-pass persistency to learn stability of variable combinations
        self.auto_conf_persistency_combos = self._new_store(
            {"converter_function": get_all_possible_combos}, classified=True
        )
        # configure inputs for the second pass; past train_buffer_max_records they spill to disk
        self.inputs = TrainBuffer(
            ParserSchema,
            max_records=self.config.train_buffer_max_records,
            spill_dir=self.config.train_buffer_dir,
            name=self.name,
        )

    def _event_data_kwargs(self) -> Optional[Dict[str, Any]]:
        return {"converter_function": get_combo}

    def _auto_conf_kwargs(self) -> Optional[Dict[str, Any]]:
        return None  # first-pass auto-config tracks individual variables

    def _prepare_variables(
        self, variables: Dict[str, Any], stage: str
    ) -> Dict[str, Any]:
        if stage == "detection":
            return cast(Dict[str, Any], get_combo(variables))
        return variables

    def _event_variables(self, input_: ParserSchema) -> List[Dict[str, Any]]:
        # every instance is its own combination; the empty group keeps an
        # event without a complete combination recorded as seen
        return list(get_instance_variables(input_, self.config.events).values()) or [{}]

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
        self.inputs.add(input_)
        super().configure(input_)

    def set_configuration(self, max_combo_size: int | None = None) -> None:
        """Set configuration based on the stability of variable combinations.

        1. Analyze individual-variable stability to identify stable variables.
        2. Generate an initial config with combos of stable variables.
        3. Re-ingest all events to learn the stability of those combos (testing
           every possible combo up front would explode combinatorially).

        Variables and combos are sorted before they are written, so the
        generated config does not depend on the order the variables arrived in
        (a ParserSchema keeps its headerVariables in no fixed order).
        """
        if max_combo_size is not None:
            self.config.auto_config_params.max_combo_size = max_combo_size

        # pass 1: stable individual variables -> combos
        variable_combos = {}
        for event_id, tracker in self.auto_conf_persistency.get_events_data().items():
            stable_vars = tracker.get_features_by_classification("STABLE")
            if len(stable_vars) > 1:
                variable_combos[event_id] = sorted(stable_vars, key=_variable_order)
        self.config.events = generate_events_config(variable_combos, self.name)  # type: ignore

        # re-ingest all inputs to learn combos under the new configuration;
        # replaying empties the buffer and removes its spill files
        for record in self.inputs:
            input_ = cast(ParserSchema, record)
            configured_variables = get_configured_variables(input_, self.config.events)
            self.auto_conf_persistency_combos.ingest_event(
                event_id=input_["eventID"],
                event_template=input_["template"],
                named_variables=configured_variables,
                timestamp=self._timestamps.read(input_),
            )

        # pass 2: stable/static combos -> final config
        combo_selection = {}
        auto = self.config.auto_config_params
        for (
            event_id,
            tracker,
        ) in self.auto_conf_persistency_combos.get_events_data().items():
            stable_combos = (
                tracker.get_features_by_classification("STABLE")
                if auto.use_stable_vars
                else []
            )
            static_combos = (
                tracker.get_features_by_classification("STATIC")
                if auto.use_static_vars
                else []
            )
            # the combo trackers are keyed by tuples of variable names
            combos = cast(List[Tuple[str, ...]], stable_combos + static_combos)
            if combos:
                combo_selection[event_id] = sorted(combos, key=_combo_order)
        self.config.events = generate_events_config(combo_selection, self.name)  # type: ignore
        self.config.auto_config = False
        if not self.config.events.events:
            logger.warning(
                f"[{self.name}] auto_config=True generated an empty configuration. "
                "No stable variable combinations were found in configure-phase data. "
                "The detector will produce no alerts."
            )
