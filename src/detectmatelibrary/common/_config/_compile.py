from detectmatelibrary.common._config._formats import EventsConfig

from typing import Any, Dict, List, Sequence, Tuple, Union
import warnings
import re


def _classify_variables(
    var_names: Sequence[str], var_pattern: re.Pattern[str]
) -> Dict[str, Any]:
    """Classify variable names into positional and header variables.

    Returns an instance config dict with 'params', 'variables', and
    'header_variables' keys.
    """
    positional_variables = []
    header_variables = []

    for var_name in var_names:
        match = var_pattern.match(var_name)
        if match:
            position = int(match.group(1))
            positional_variables.append({
                "pos": position,
                "name": var_name,
                "params": {}
            })
        else:
            header_variables.append({
                "pos": var_name,
                "params": {}
            })

    instance_config: Dict[str, Any] = {"params": {}}
    if positional_variables:
        instance_config["variables"] = positional_variables
    if header_variables:
        instance_config["header_variables"] = header_variables

    return instance_config


class MethodNotFoundError(Exception):
    def __init__(self, method_id: str, comp_type: str) -> None:
        super().__init__(
            f"Method '{method_id}' of type '{comp_type}' not found in configuration."
        )


class TypeNotFoundError(Exception):
    def __init__(self, type_name: str) -> None:
        super().__init__(f"Type '{type_name}' not found in configuration.")


class MethodTypeNotMatch(Exception):
    def __init__(self, expected_type: str, actual_type: str) -> None:
        super().__init__(
            f"Type mismatch: expected '{expected_type}', got '{actual_type}'."
        )


class MissingParamsWarning(UserWarning):
    def __init__(self) -> None:
        super().__init__("'auto_config = False' and no 'params' or 'events' provided. Is that intended?")


class AutoConfigWarning(UserWarning):
    def __init__(self) -> None:
        super().__init__("'auto_config = True' will overwrite 'events' and 'params'.")


class ConfigMethods:
    @staticmethod
    def get_method(
        config: Dict[str, Dict[str, Dict[str, Any]]], method_id: str, comp_type: str
    ) -> Dict[str, Any]:

        if comp_type not in config:
            raise TypeNotFoundError(comp_type)

        args = config[comp_type]
        if method_id not in args:
            raise MethodNotFoundError(method_id, comp_type)

        return args[method_id]

    @staticmethod
    def check_type(config: Dict[str, Any], method_type: str) -> None:
        if config["method_type"] != method_type:
            raise MethodTypeNotMatch(expected_type=method_type, actual_type=config["method_type"])

    @staticmethod
    def process(config: Dict[str, Any]) -> Dict[str, Any]:
        has_params = "params" in config
        has_events = "events" in config

        if not has_params and not has_events and not config.get("auto_config", False):
            warnings.warn(MissingParamsWarning())

        if has_params:
            if config.get("auto_config", False):
                warnings.warn(AutoConfigWarning())

            config.update(config["params"])
            config.pop("params")

        # Handle "events" key at top level
        if has_events:
            config["events"] = EventsConfig._init(config["events"])

        return config


def generate_detector_config(
    variable_selection: Dict[int, List[Union[str, Tuple[str, ...]]]],
    detector_name: str,
    method_type: str,
    **additional_params: Any
) -> Dict[str, Any]:
    """Generate a detector configuration dictionary from variable selections.

    Transforms a variable selection mapping into the nested configuration
    structure required by detector configs. Supports both individual variable
    names (strings) and tuples of variable names. Each tuple produces a
    separate detector instance in the config.

    Args:
        variable_selection: Maps event_id to list of variable names or tuples
            of variable names. Strings are grouped into a single instance.
            Each tuple becomes its own instance. Variable names matching
            'var_\\d+' are positional template variables; others are header
            variables.
        detector_name: Name of the detector, used as the base instance_id.
        method_type: Type of detection method (e.g., "new_value_detector").
        **additional_params: Additional parameters for the detector's params
            dict (e.g., comb_size=3).

    Returns:
        Dictionary with structure compatible with detector config classes.

    Examples:
        Single variable names (one instance per event)::

            config = generate_detector_config(
                variable_selection={1: ["var_0", "var_1", "level"]},
                detector_name="MyDetector",
                method_type="new_value_detector",
            )

        Tuples of variable names (one instance per tuple)::

            config = generate_detector_config(
                variable_selection={1: [("username", "src_ip"), ("var_0", "var_1")]},
                detector_name="MyDetector",
                method_type="new_value_combo_detector",
                comb_size=2,
            )
    """
    var_pattern = re.compile(r"^var_(\d+)$")

    events_config: Dict[int, Dict[str, Any]] = {}

    for event_id, variable_names in variable_selection.items():
        instances: Dict[str, Any] = {}

        # Separate plain strings from tuples
        single_vars: List[str] = []
        tuple_vars: List[Tuple[str, ...]] = []

        for entry in variable_names:
            if isinstance(entry, tuple):
                tuple_vars.append(entry)
            else:
                single_vars.append(entry)

        # Plain strings -> single instance keyed by detector_name
        if single_vars:
            instances[detector_name] = _classify_variables(single_vars, var_pattern)

        # Each tuple -> its own instance, keyed by joined variable names
        for combo in tuple_vars:
            instance_id = f"{detector_name}_{'_'.join(combo)}"
            instances[instance_id] = _classify_variables(combo, var_pattern)

        events_config[event_id] = instances

    config_dict = {
        "detectors": {
            detector_name: {
                "method_type": method_type,
                "auto_config": False,
                "params": additional_params,
                "events": events_config
            }
        }
    }

    return config_dict
