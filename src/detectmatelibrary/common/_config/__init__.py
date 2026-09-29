from ._compile import ConfigMethods, generate_detector_config, generate_events_config
from ._formats import EventsConfig

__all__ = [
    "ConfigMethods",
    "generate_detector_config",
    "generate_events_config",
    "EventsConfig",
    "BasicConfig",
    "AutoConfigParams",
]

from pydantic import BaseModel, ConfigDict, Field

from typing_extensions import Self
from typing import Any, Dict
from copy import deepcopy

from numpy.random import choice
import string


def random_id(length: int = 10) -> str:
    characters = [s for s in string.ascii_letters + string.digits]
    return "".join(str(choice(characters)) for _ in range(length))


class AutoConfigParams(BaseModel):
    """Inputs to the auto-configuration (configure) phase.

    Empty here: no component has configure-phase inputs by default. Subclasses
    add the fields their own configure phase reads. Kept apart from the
    operational `params` block so the phase a setting belongs to is visible in
    the YAML, not just in the code that reads it.

    Lives beside `auto_config` on `BasicConfig` rather than on any one
    component type: `auto_config` and `Component.configure()` are both declared
    at the base, so the block that feeds that phase belongs there too. Empty by
    default, and `to_dict` omits it while it stays at its default, so a
    component whose configure phase takes no inputs serializes exactly as it
    did before this block existed.
    """

    model_config = ConfigDict(extra="forbid")


class BasicConfig(BaseModel):
    """Base configuration class with helper methods."""

    model_config = ConfigDict(extra="forbid")

    method_type: str = Field(
        default="default_method_type", description="Indicates what type of method is."
    )
    component_type: str = Field(
        default="default_type",
        description="Component type that the class inherent from.",
    )

    auto_config: bool = Field(
        default=False,
        description="Runs the configuration step before the training process.",
    )

    auto_config_params: AutoConfigParams = Field(
        default=AutoConfigParams(), description="<$IGNORE$>"
    )

    def get_docs(
        self, shared_base: "type[BasicConfig] | None" = None
    ) -> list[dict[str, Any]]:
        """List this config's fields as doc rows, one per YAML setting.

        ``auto_config_params`` is expanded into one row per field (nested
        models as dotted names, e.g. ``classification.decision``); fields whose
        description contains ``<$IGNORE$>`` are left out.

        Args:
            shared_base: the family base this config is documented against.
                A field that also exists there is ``shared``, otherwise
                ``specific``; a shared field whose default this config changes
                is flagged, with the base's default in ``Shared default``.
                Without a base, every field is ``specific``.
        """
        return _doc_rows(self, shared_base)

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
            deepcopy(data), component_type=aux.component_type, method_id=method_id
        )
        ConfigMethods.check_type(config_, method_type=aux.method_type)

        return cls(**ConfigMethods.process(config_))

    def to_dict(self, method_id: str = random_id()) -> Dict[str, Any]:
        """Convert the config back to YAML-compatible dictionary format.

        This is the inverse of from_dict() and ensures yaml -> pydantic -> yaml preservation.

        Args:
            method_id: The method identifier to use in the output structure

        Returns:
            Dictionary with structure: {component_type: {method_id: config_data}}
        """
        # Build the config in the format expected by from_dict
        result: Dict[str, Any] = {
            "method_type": self.method_type,
            "auto_config": self.auto_config,
        }

        # Collect all non-meta fields for params
        params = {}
        events_data = None
        instances_data = None
        persist_data: dict[str, Any] | None = None
        auto_params_data: dict[str, Any] | None = None

        for field_name, field_value in self:
            # Skip meta fields
            if field_name in ("component_type", "method_type", "auto_config"):
                continue

            # Handle EventsConfig specially
            if field_name == "events":
                if field_value is not None:
                    if isinstance(field_value, EventsConfig):
                        events_data = field_value.to_dict()
                    else:
                        events_data = field_value
            # Its own top-level block, and only when it differs from the
            # default -- a config that never touches auto-config must serialize
            # exactly as it did before this block existed.
            elif field_name == "auto_config_params":
                if field_value != type(self).model_fields[field_name].default:
                    auto_params_data = field_value.model_dump()
            # Handle global instances specially (top-level, not in params)
            # Serialized as "global" in YAML (Python field is "global_instances")
            elif field_name == "global_instances" and field_value:
                instances_data = {
                    name: inst.to_dict() for name, inst in field_value.items()
                }
            elif field_name == "persist":
                if field_value is not None:
                    persist_data = field_value.model_dump()
            else:
                # All other fields go into params
                params[field_name] = field_value

        # Add params if there are any
        if params:
            result["params"] = params

        if auto_params_data is not None:
            result["auto_config_params"] = auto_params_data

        # Add global instances if they exist (serialized as "global" in YAML)
        if instances_data is not None:
            result["global"] = instances_data

        # Add events if they exist
        if events_data is not None:
            result["events"] = events_data

        if persist_data is not None:
            result["persist"] = persist_data

        # Wrap in the component_type and method_id structure
        return {self.component_type: {method_id: result}}


# Where each field lands in the YAML written by BasicConfig.to_dict(): these
# stay beside method_type, auto_config_params is a block of its own, and every
# other field goes under params.
_TOP_LEVEL_FIELDS = ("method_type", "component_type", "auto_config", "events", "global_instances", "persist")
_YAML_NAMES = {"global_instances": "global"}
_AUTO_CONFIG_BLOCK = "auto_config_params"
_NO_DESCRIPTION = "No description provided."


def _schema_type(field_schema: Dict[str, Any]) -> str:
    """JSON-schema type of one field; a nested model reads as ``object``."""
    if "type" in field_schema:
        return str(field_schema["type"])
    if "anyOf" in field_schema:
        types = [str(item.get("type", "object")) for item in field_schema["anyOf"]]
        return ", ".join(dict.fromkeys(types))
    if "$ref" in field_schema or "allOf" in field_schema:
        return "object"
    return "unknown"


def _doc_rows(
    model: BaseModel,
    base_cls: type[BaseModel] | None,
    block: str | None = None,
    prefix: str = "",
) -> list[dict[str, Any]]:
    """Doc rows for ``model``'s fields, scoped against ``base_cls``.

    ``block`` is None for the config itself (each field is then placed as
    to_dict() places it) and the block name while recursing into
    ``auto_config_params``, where nested models become dotted names.
    """
    rows: list[dict[str, Any]] = []
    base_fields = base_cls.model_fields if base_cls is not None else {}
    properties = type(model).model_json_schema().get("properties", {})
    for name, field_schema in properties.items():
        value = getattr(model, name)
        in_base = name in base_fields
        base_default = base_fields[name].get_default(call_default_factory=True) if in_base else None

        expand = name == _AUTO_CONFIG_BLOCK if block is None else isinstance(value, BaseModel)
        if expand:
            rows += _doc_rows(
                value,
                type(base_default) if isinstance(base_default, BaseModel) else None,
                block=block or _AUTO_CONFIG_BLOCK,
                prefix="" if block is None else f"{prefix}{name}.",
            )
            continue

        desc = field_schema.get("description", _NO_DESCRIPTION)
        if "<$IGNORE$>" in desc:
            continue
        # Not flagged: every component sets its own method_type, and a dict
        # default (e.g. hyperparameters) is a template the subclass fills in.
        changed = (
            in_base and name != "method_type" and not isinstance(value, dict) and value != base_default
        )
        rows.append(
            {
                "Name": prefix + (_YAML_NAMES.get(name, name) if block is None else name),
                "Block": block or ("top" if name in _TOP_LEVEL_FIELDS else "params"),
                "Type": _schema_type(field_schema),
                "Default value": value,
                "Scope": "shared" if in_base else "specific",
                "Default changed": changed,
                "Shared default": base_default if changed else None,
                "Description": desc,
            }
        )
    return rows
