
from detectmatelibrary.common._config._formats import apply_format


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

        return args[method_id]    # type: ignore

    @staticmethod
    def check_type(config: Dict[str, Any], method_type: str) ->  MethodTypeNotMatch | None:
        if config["method_type"] != method_type:
           raise MethodTypeNotMatch( expected_type=method_type, actual_type=config["method_type"])
        return None

    @staticmethod
    def process(config: Dict[str, Any]) -> Dict[str, Any] | AutoConfigError | MissingFormat:
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
