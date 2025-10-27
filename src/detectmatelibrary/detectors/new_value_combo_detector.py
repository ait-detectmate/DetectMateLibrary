from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.utils.functions import sorted_int_str
import detectmatelibrary.schemas as schemas

from itertools import combinations

from typing import List, Any, Set, Dict


class ComboTooBigError(Exception):
    def __init__(self, exp_size: int, max_size: int) -> None:
        super().__init__(f"Expected size {exp_size} but the max it got {max_size}")


def _get_element(input_: schemas.ParserSchema, var_pos: str | int) -> Any:
    if isinstance(var_pos, str):
        return input_.logFormatVariables[var_pos]
    elif len(input_.variables) > var_pos:
        return input_.variables[var_pos]


def train_combo_detector(
    input_: schemas.ParserSchema,
    known_combos: Dict[str | int, Set[Any]],
    combo_size: int,
    log_variables: LogVariables | AllLogVariables
) -> None:

    relevant_log_fields = log_variables[input_.EventID]
    if relevant_log_fields is None:
        return
    relevant_log_fields = relevant_log_fields.get_all().keys()

    if len(relevant_log_fields) < combo_size:
        raise ComboTooBigError(combo_size, len(relevant_log_fields))

    unique_combos = set(combinations([
        _get_element(input_, var_pos=field) for field in relevant_log_fields
    ], combo_size))

    if isinstance(log_variables, LogVariables):
        if input_.EventID not in known_combos:
            known_combos[input_.EventID] = set()
        known_combos[input_.EventID] = known_combos[input_.EventID].union(unique_combos)
    else:
        known_combos["all"] = known_combos["all"].union(unique_combos)


class NewValueComboDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_combo_detector"

    log_variables: LogVariables | AllLogVariables = {}
    comb_size: int = 2


class NewValueComboDetector(CoreDetector):
    """Detect new values in log data as anomalies based on learned values."""

    def __init__(
        self,
        name: str = "NewValueComboDetector",
        config: NewValueComboDetectorConfig = NewValueComboDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewValueComboDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode="no_buf", config=config)
        self.known_combos = {"all": set()}

    def train(self, input_: schemas.ParserSchema) -> None:
        train_combo_detector(
            input_=input_,
            known_combos=self.known_combos,
            combo_size=self.config.comb_size,
            log_variables=self.config.log_variables
        )

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data."""
        overall_score = 0.0
        alerts = {}
        # get the relevant parts of a log based on config
        relevant_log_fields = self.config.get_relevant_fields(input_)

        var_combo = tuple(sorted_int_str(relevant_log_fields.keys()))
        if var_combo in self.known_combos.get(input_.EventID, []):
            val_combo = tuple(field["value"] for field in relevant_log_fields.values())
            is_combo_known = val_combo in self.known_combos[input_.EventID][var_combo]
            if not is_combo_known:
                score = 1.0
                alerts.update({str(val_combo): str(score)})
            overall_score += score
        if overall_score > 0:
            output_.score = overall_score
            # Use update() method for protobuf map fields
            output_.alertsObtain.update(alerts)
            return True
        return False
