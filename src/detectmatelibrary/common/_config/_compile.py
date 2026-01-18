
from detectmatelibrary.common._config._formats import apply_format


from typing import Any, Dict, List, Optional
from copy import deepcopy
import warnings


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


class AutoConfigError(Exception):
    def __init__(self) -> None:
        super().__init__("When auto_config = False, there must be a params field.")


class AutoConfigWarning(UserWarning):
    def __init__(self) -> None:
        super().__init__("auto_config = True will overwrite your params.")


class MissingFormat(Exception):
    def __init__(self) -> None:
        super().__init__("params is a list an is missing its format id")


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
    def check_type(config: Dict[str, Any], method_type: str) -> MethodTypeNotMatch | None:
        if config["method_type"] != method_type:
            raise MethodTypeNotMatch(expected_type=method_type, actual_type=config["method_type"])
        return None

    @staticmethod
    def process(config: Dict[str, Any]) -> Dict[str, Any]:
        if "params" not in config and not config["auto_config"]:
            raise AutoConfigError()

        if "params" in config:
            if config["auto_config"]:
                warnings.warn(AutoConfigWarning())
            if isinstance(config["params"], list):
                raise MissingFormat()

            for param in config["params"].copy():
                config["params"][param.replace("all_", "")] = apply_format(
                    param, config["params"][param]
                )
                if "all_" in param:
                    config["params"].pop(param)

            config.update(config["params"])
            config.pop("params")
        return config


def generate_detector_config(
    variable_selection: Dict[int, List[str]],
    templates: Dict[Any, str | None],
    detector_name: str,
    method_type: str,
    base_config: Optional[Dict[str, Any]] = None,
    **additional_params: Any,
) -> Dict[str, Any]:
    """Generate the configuration for detectors. Output is a dictionary.

    Args:
        variable_selection (Dict[int, List[str]]): Mapping of event IDs to variable names.
        templates (Dict[Any, str | None]): Mapping of event IDs to their templates.
        detector_name (str): Name of the detector.
        method_type (str): Type of the detection method.
        base_config (Optional[Dict[str, Any]]): Base configuration to build upon.
        **additional_params: Additional parameters for the detector.
    """

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
    params.update(additional_params)
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
