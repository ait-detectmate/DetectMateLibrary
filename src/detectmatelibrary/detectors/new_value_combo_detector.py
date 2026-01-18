from detectmatelibrary.common._config._formats import LogVariables, AllLogVariables

from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.detector import CoreDetector

from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary.common.persistency.event_data_structures.trackers import (
    EventVariableTracker, StabilityTracker
)
from detectmatelibrary.common.persistency.event_persistency import EventPersistency

import detectmatelibrary.schemas as schemas

from itertools import combinations

from typing import Any, Set, Dict, cast

from copy import deepcopy
from typing import List, Optional


def generate_detector_config(
    variable_selection: Dict[int, List[str]],
    templates: Dict[Any, str | None],
    detector_name: str,
    method_type: str,
    base_config: Optional[Dict[str, Any]] = None,
    max_combo_size: int = 6,
) -> Dict[str, Any]:

    if base_config is None:
        base_config = {
            "detectors": {
                detector_name: {
                    "method_type": method_type,
                    "auto_config": False,
                    "params": {
                        "log_variables": []
                    },
                }
            }
        }
    config = deepcopy(base_config)

    detectors = config.setdefault("detectors", {})
    detector = detectors.setdefault(detector_name, {})
    detector.setdefault("method_type", method_type)
    detector.setdefault("auto_config", False)
    params = detector.setdefault("params", {})
    params["comb_size"] = max_combo_size
    log_variables = params.setdefault("log_variables", [])

    for event_id, all_variables in variable_selection.items():
        variables = [
            {"pos": int(name.split("_")[1]), "name": name}
            for name in all_variables if name.startswith("var_")
        ]
        header_variables = [{"pos": name} for name in all_variables if not name.startswith("var_")]

        log_variables.append({
            "id": f"id_{event_id}",
            "event": event_id,
            "template": templates.get(event_id, ""),
            "variables": variables,
            "header_variables": header_variables,
        })
    return config


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
        return input_["logFormatVariables"][var_pos]
    elif len(input_["variables"]) > var_pos:
        return input_["variables"][var_pos]


def _get_combos(
    input_: schemas.ParserSchema,
    combo_size: int,
    log_variables: LogVariables | AllLogVariables
) -> Set[Any]:

    relevant_log_fields = log_variables[input_["EventID"]]
    if relevant_log_fields is None:
        return set()

    relevant_log_fields = relevant_log_fields.get_all().keys()  # type: ignore
    # _check_size(combo_size, len(relevant_log_fields))  # type: ignore

    return set(combinations([
        _get_element(input_, var_pos=field) for field in relevant_log_fields  # type: ignore
    ], combo_size))


# Combo detector methods ********************************************************
def train_combo_detector(
    input_: schemas.ParserSchema,
    known_combos: Dict[str | int, Set[Any]],
    combo_size: int,
    log_variables: LogVariables | AllLogVariables
) -> None:

    if input_["EventID"] not in log_variables:
        return None
    unique_combos = _get_combos(
        input_=input_, combo_size=combo_size, log_variables=log_variables
    )

    if isinstance(log_variables, LogVariables):
        if input_["EventID"] not in known_combos:
            known_combos[input_["EventID"]] = set()
        known_combos[input_["EventID"]] = known_combos[input_["EventID"]].union(unique_combos)
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
    if input_["EventID"] in log_variables:
        unique_combos = _get_combos(
            input_=input_, combo_size=combo_size, log_variables=log_variables
        )

        if isinstance(log_variables, AllLogVariables):
            combos_set = known_combos["all"]
        else:
            combos_set = known_combos[input_["EventID"]]

        if not unique_combos.issubset(combos_set):
            for combo in unique_combos - combos_set:
                overall_score += 1
                alerts.update({f"EventID_{input_['EventID']}": f"Values: {combo}"})

    return overall_score


#  *********************************************************************
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
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.config: NewValueComboDetectorConfig

        self.config = cast(NewValueComboDetectorConfig, self.config)
        self.known_combos: Dict[str | int, Set[Any]] = {"all": set()}
        self.persistency = EventPersistency(
            event_data_class=EventVariableTracker,
            event_data_kwargs={"tracker_type": StabilityTracker}
        )

    def train(self, input_: schemas.ParserSchema) -> None:  # type: ignore
        # self.persistency.ingest_event(
        #     event_id=input_["EventID"],
        #     event_template=input_["template"],
        #     variables=input_["variables"],
        #     log_format_variables=input_["logFormatVariables"],
        # )
        train_combo_detector(
            input_=input_,
            known_combos=self.known_combos,
            combo_size=self.config.comb_size,
            log_variables=self.config.log_variables  # type: ignore
        )

    def detect(
        self, input_: schemas.ParserSchema, output_: schemas.DetectorSchema  # type: ignore
    ) -> bool:
        alerts: Dict[str, str] = {}

        overall_score = detect_combo_detector(
            input_=input_,
            known_combos=self.known_combos,
            combo_size=self.config.comb_size,
            log_variables=self.config.log_variables,  # type: ignore
            alerts=alerts,
        )

        if overall_score > 0:
            output_["score"] = overall_score
            output_["description"] = (
                f"The detector checks for new value combinations of size {self.config.comb_size}."
            )
            output_["alertsObtain"].update(alerts)
            return True
        return False

    def configure(self, input_: schemas.ParserSchema) -> None:
        self.persistency.ingest_event(
            event_id=input_["EventID"],
            event_template=input_["template"],
            variables=input_["variables"],
            log_format_variables=input_["logFormatVariables"],
        )

    def set_configuration(self, max_combo_size: int = 6) -> None:
        variable_combos = {}
        templates = {}
        for event_id, tracker in self.persistency.get_events_data().items():
            stable_vars = tracker.get_stable_variables()  # type: ignore
            if len(stable_vars) > 1:
                variable_combos[event_id] = stable_vars
                templates[event_id] = self.persistency.get_event_template(event_id)
        config_dict = generate_detector_config(
            variable_selection=variable_combos,
            templates=templates,
            detector_name=self.name,
            method_type=self.config.method_type,
            max_combo_size=max_combo_size
        )
        # Update the config object from the dictionary instead of replacing it
        self.config = NewValueComboDetectorConfig.from_dict(config_dict, self.name)
