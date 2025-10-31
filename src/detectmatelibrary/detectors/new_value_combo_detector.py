from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.utils.data_buffer import BufferMode

import detectmatelibrary.schemas as schemas

from itertools import combinations

from typing import List, Any, Set, Dict, cast


# Auxiliar methods ********************************************************
class ComboTooBigError(Exception):
    def __init__(self, exp_size: int, max_size: int) -> None:
        super().__init__(f"Expected size {exp_size} but the max it got {max_size}")


def _check_size(exp_size: int, max_size: int) -> None | ComboTooBigError:
    if max_size < exp_size:
        raise ComboTooBigError(exp_size, max_size)
    return None


def _get_element(input_: schemas.ParserSchema, var_pos: str | int) -> Any:
    if isinstance(var_pos, str):
        return input_.logFormatVariables[var_pos]
    elif len(input_.variables) > var_pos:
        return input_.variables[var_pos]


def _get_combos(
    input_: schemas.ParserSchema,
    combo_size: int,
    log_variables: LogVariables | AllLogVariables
) -> Set[Any]:

    relevant_log_fields = log_variables[input_.EventID]
    if relevant_log_fields is None:
        return set()

    relevant_log_fields = relevant_log_fields.get_all().keys()   # type: ignore
    _check_size(combo_size, len(relevant_log_fields))   # type: ignore

    return set(combinations([
        _get_element(input_, var_pos=field) for field in relevant_log_fields    # type: ignore
    ], combo_size))


# Combo detector methods ********************************************************
def train_combo_detector(
    input_: schemas.ParserSchema,
    known_combos: Dict[str | int, Set[Any]],
    combo_size: int,
    log_variables: LogVariables | AllLogVariables
) -> None:

    if input_.EventID not in log_variables:
        return
    unique_combos = _get_combos(
        input_=input_, combo_size=combo_size, log_variables=log_variables
    )

    if isinstance(log_variables, LogVariables):
        if input_.EventID not in known_combos:
            known_combos[input_.EventID] = set()
        known_combos[input_.EventID] = known_combos[input_.EventID].union(unique_combos)
    else:
        known_combos["all"] = known_combos["all"].union(unique_combos)


def detect_combo_detector(
    input_: schemas.ParserSchema,
    known_combos: Dict[str | int, Set[Any]],
    combo_size: int,
    log_variables: LogVariables | AllLogVariables,
    alerts: dict[str, str],
) -> int:

    overall_score = 0
    if input_.EventID in log_variables:
        unique_combos = _get_combos(
            input_=input_, combo_size=combo_size, log_variables=log_variables
        )

        if isinstance(log_variables, AllLogVariables):
            combos_set = known_combos["all"]
        else:
            combos_set = known_combos[input_.EventID]

        if not unique_combos.issubset(combos_set):
            for combo in unique_combos - combos_set:
                overall_score += 1
                alerts.update({"Not found combo": str(combo)})

    return overall_score

# *********************************************************************

class NewValueComboDetectorConfig(CoreDetectorConfig):
    method_type: str = "new_value_combo_detector"

    log_variables: LogVariables | AllLogVariables | dict[str, Any] = {}
    comb_size: int = 2


class NewValueComboDetector(CoreDetector):
    def __init__(
        self,
        name: str = "NewValueComboDetector",
        config: NewValueComboDetectorConfig = NewValueComboDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = NewValueComboDetectorConfig.from_dict(config, name)
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUFF, config=config)

        self.config = cast(NewValueComboDetectorConfig, self.config)
        self.known_combos: Dict[str | int, Set[Any]] = {"all": set()}

    def train(self, input_: schemas.ParserSchema) -> None:
        train_combo_detector(
            input_=input_,
            known_combos=self.known_combos,
            combo_size=self.config.comb_size,   # type: ignore
            log_variables=self.config.log_variables   # type: ignore
        )

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        alerts: Dict[str, str] = {}

        overall_score = detect_combo_detector(
            input_=input_,
            known_combos=self.known_combos,
            combo_size=self.config.comb_size,   # type: ignore
            log_variables=self.config.log_variables,   # type: ignore
            alerts=alerts,
        )

        if overall_score > 0:
            output_.score = overall_score
            output_.description = f"The detector check combinations of {self.config.comb_size} variables"   # type: ignore
            output_.alertsObtain.update(alerts)
            return True
        return False
