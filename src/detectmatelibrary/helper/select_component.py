from detectmatelibrary.common.core import CoreConfig, CoreComponent
from detectmatelibrary import detectors, parsers, alert_aggregation
from detectmatelibrary.schemas import BaseSchema

from typing import Optional, Any

# --------------------- Auxiliar
__types = {
    "parsers": parsers,
    "detectors": detectors,
    "alert_aggregators": alert_aggregation
}


def _find_component_from_type(
    method_type: str, component_type: str
) -> Optional[type[CoreComponent[BaseSchema, BaseSchema]]]:

    for obj in dir(module := __types[component_type]):
        try:
            if isinstance(conf := getattr(module, obj)(), CoreConfig):  # Look for config
                if conf.method_type == method_type:
                    for comp in dir(__types[component_type]):  # Look for Component
                        try:
                            if isinstance(comp_ := getattr(module, comp)(), CoreComponent):
                                if type(comp_.config) == type(conf):  # noqa: E721
                                    return getattr(module, comp)  # type: ignore
                        except TypeError:
                            pass
        except TypeError:
            pass

    return None


# --------------------------------- Main methods
def selectComponent(
    config: CoreConfig | dict[str, Any], component_type: str, name: Optional[str] = None
) -> CoreComponent:
    """Component, I pick you!!!

    If name=None, it will check in the config
    """

    if isinstance(config, CoreConfig):
        method_type = config.method_type
        name = name if name is not None else "pickedComponent"

    else:
        if name is None:
            name = list(config[component_type].keys())[0]

        method_type = config[component_type][name]["method_type"]

    component = _find_component_from_type(method_type, component_type=component_type)
    if component is None:
        raise ValueError(f"{method_type} form {component_type} not found.")

    return component(name=name, config=config)


def selectComponents(
    configs: list[CoreConfig | dict[str, Any]],
    component_type: str,
    names: Optional[list[str | None]] = None
) -> list[CoreComponent]:

    if names is None:
        names = [None for _ in configs]

    return [
        selectComponent(config=config, component_type=component_type, name=name)
        for config, name in zip(configs, names)
    ]
