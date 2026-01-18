from detectmatelibrary.common._config._compile import ConfigMethods

from pydantic import BaseModel, ConfigDict

from typing_extensions import Self
from typing import Any, Dict, List, Optional
from copy import deepcopy


class BasicConfig(BaseModel):
    """Base configuration class with helper methods."""

    model_config = ConfigDict(extra="forbid")

    method_type: str = "default_method_type"
    comp_type: str = "default_type"

    auto_config: bool = False

    def get_config(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self.model_dump()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update the configuration with new values."""
        for key, value in new_config.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], method_id: str) -> Self:
        aux = cls()
        config_ = ConfigMethods.get_method(
            deepcopy(data), comp_type=aux.comp_type, method_id=method_id
        )
        ConfigMethods.check_type(config_, method_type=aux.method_type)

        return cls(**ConfigMethods.process(config_))


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
