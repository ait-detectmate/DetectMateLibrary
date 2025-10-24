from detectmatelibrary.utils._formats import choose_format, init_format

from pydantic import BaseModel
from typing import Any, Dict
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
        super().__init__("When auto_config = False, there must a params field.")


class AutoConfigWarning(UserWarning):
    def __init__(self) -> None:
        super().__init__("auto_config = True will overwrite your params.")


class MissingFormat(Exception):
    def __init__(self) -> None:
        super().__init__("params is a list an is missing its format id")


class ConfigMethods:
    @staticmethod
    def get_method(
        config: Dict[str, Any], method_id: str, comp_type: str
    ) -> Dict[str, Any] | MethodNotFoundError | TypeNotFoundError:

        if comp_type not in config:
            raise TypeNotFoundError(comp_type)

        args = config[comp_type]
        if method_id not in args:
            raise MethodNotFoundError(method_id, comp_type)

        return args[method_id]

    @staticmethod
    def check_type(config: Dict[str, Any], method_type: str) ->  MethodTypeNotMatch | None:
       if config["method_type"] != method_type:
           raise MethodTypeNotMatch( expected_type=method_type, actual_type=config["method_type"])

    @staticmethod
    def process(config: Dict[str, Any]) -> Dict[str, Any] | AutoConfigError | MissingFormat:
        if "params" not in config and not config["auto_config"]:
            raise AutoConfigError()

        if "params" in config:
            if config["auto_config"]:
                warnings.warn(AutoConfigWarning())
            if isinstance(config["params"], list):
                raise MissingFormat()

            for param in config["params"]:
                use_format, format_ = choose_format(param)
                if use_format:
                    config["params"][param] = init_format(format_, config["params"][param])

            config.update(config["params"])
            config.pop("params")

        return config




class BasicConfig(BaseModel):
    """Base configuration class with helper methods."""

    # Forbid extra fields not defined in subclasses (via pydantic)
    class Config:
        extra = "forbid"

    method_id: str = "default_method"
    method_type: str = "default_type"
    auto_config: bool = False

    def get_config(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self.model_dump()

    def update_config(self, new_config: dict) -> None:
        """Update the configuration with new values."""
        for key, value in new_config.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: dict) -> "BasicConfig":
        return compile_config(data, cls)
