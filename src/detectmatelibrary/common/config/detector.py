from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator
from typing import List, Literal, Optional, Union
import warnings
import re

from components.common.core import CoreConfig
import schemas as schemas


class DetectorVariableBase(BaseModel):
    params: Optional[Union[dict, BaseModel]] = None

    @field_serializer('params')
    def serialize_params(self, params: Optional[Union[dict, BaseModel]]) -> Optional[dict]:
        """Serialize params field, handling BaseModel objects properly."""
        if params is None:
            return None
        if isinstance(params, BaseModel):
            return params.model_dump()
        return params


class DetectorVariable(DetectorVariableBase):
    # header variables use string IDs (e.g., Level, Time)
    pos: Union[int, str]


class DetectorInstance(BaseModel):
    id: str
    event: Union[int, Literal["all"]]
    template: Optional[str] = None
    variables: Optional[List[DetectorVariable]] = None
    # Temporary field for YAML parsing - will be merged into variables
    header_variables_input: Optional[List[DetectorVariable]] = Field(
        default=None,
        alias="header-variables",
        description="Temporary field for header variables from YAML input.",
        exclude=True,  # Exclude from serialization
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("event")
    @classmethod
    def _non_negative_event(cls, v):
        if isinstance(v, int) and v < 0:
            raise ValueError("event must be >= 0 or 'all'")
        return v

    @model_validator(mode="after")
    def _combine_variables(self):
        """Combine variables and header_variables into a single variables
        list."""
        all_variables = []

        # Add regular variables
        if self.variables:
            all_variables.extend(self.variables)

        # Add header variables from the temporary field
        if self.header_variables_input:
            all_variables.extend(self.header_variables_input)

        # Update the variables field with the combined list
        self.variables = all_variables if all_variables else None

        return self

    @model_validator(mode="after")
    def _warn_on_out_of_range_variable_ids(self):
        """If a template is provided, count occurrences of '<*>' and warn when
        a variable.id falls outside that range (as your example suggests).

        Only applies to DetectorVariable instances with integer IDs.
        """
        if self.template and self.variables:
            # Count "<*>" occurrences very literally:
            m = re.findall(r"<\*>", self.template)
            slot_count = len(m)
            for var in self.variables:
                # Only check integer IDs (DetectorVariable), skip string IDs (HeaderVariable)
                if isinstance(var.pos, int):
                    if var.pos < 0:
                        warnings.warn(
                            f"[{self.id}] Variable id {var.pos} is negative; it will be ignored.",
                            stacklevel=2,
                        )
                    elif slot_count and var.pos >= slot_count:
                        warnings.warn(
                            f"[{self.id}] Variable id {var.pos} out of range for template with {slot_count} "
                            f"slots; will be ignored.",
                            stacklevel=2,
                        )
        return self


class CoreDetectorConfig(CoreConfig):
    """Generic detector config; allows extra fields to support detector-
    specific settings."""

    detectorID: str = "<PLACEHOLDER>"
    detectorType: str = "<PLACEHOLDER>"
    parser: Optional[str] = Field(
        default=None,
        description="If present, must reference a ParserInstance.id.",
    )
    auto_config: bool = False
    instances: List[DetectorInstance] = []

    _n_instances: Optional[int] = None
    _all_instances: Optional[List] = None
    _all_instances_dict: Optional[dict] = None

    @model_validator(mode="after")
    def _calculate_instances(self):
        """Calculate total number of variables across all instances."""
        all_instances = []
        all_instances_dict = {}
        if self.instances:
            for i in self.instances:
                instance = (
                    i
                    if isinstance(i, DetectorInstance)
                    else DetectorInstance.model_validate(i)
                )
                variables = getattr(instance, "variables") or []
                all_instances += [(instance.event, var) for var in variables if var]
                variable_dict = {var.pos: var for var in variables}
                all_instances_dict.update({instance.event: variable_dict})
        self._all_instances = all_instances
        self._n_instances = len(self._all_instances)
        self._all_instances_dict = all_instances_dict
        return self

    @model_validator(mode="after")
    def _instances_required_if_not_auto(self):
        if not self.auto_config and (
            self.instances is None or len(self.instances) == 0
        ):
            warning = f"Detector '{self.detectorType}' has auto_config=false, but no explicit instances."
            warnings.warn(
                warning,
                UserWarning,
            )
        return self

    def get_number_of_instances(self) -> int:
        """Return the number of instances, calculating if necessary."""
        if self._n_instances is None:
            self._calculate_instances()
        return self._n_instances

    def get_all_instances(self) -> int:
        """Return a list of all DetectInstances."""
        return self._all_instances

    def get_all_instances_dict(self) -> dict:
        """Return a dict of all DetectInstances, keyed by event ID."""
        return self._all_instances_dict

    def add_instance(
        self,
        instance: Optional[DetectorInstance] = None,
        *,
        pos: Optional[str] = None,
        event: Optional[Union[int, Literal["all"]]] = None,
        template: Optional[str] = None,
        variables: Optional[List[DetectorVariable]] = None,
        header_variables: Optional[List[DetectorVariable]] = None,
    ) -> None:
        """Add a DetectorInstance to this config."""
        if instance is not None:
            # Use the provided instance directly
            if not isinstance(instance, DetectorInstance):
                raise TypeError("instance must be a DetectorInstance object")
            new_instance = instance
        else:
            # Create instance from parameters
            if pos is None or event is None:
                raise ValueError("id and event are required when instance is not provided")

            new_instance = DetectorInstance(
                id=pos,
                event=event,
                template=template,
                variables=variables or [],
                header_variables=header_variables or []
            )
        self.instances.append(new_instance)
        # Recalculate number of all instances
        self._calculate_instances()

    def get_relevant_fields(self, data: schemas.ParserSchema) -> dict:
        """Get relevant fields for a given log entry based on the detector
        configuration."""
        all_variables = {**data.logFormatVariables, **dict(enumerate(data.variables))}
        configured_instances = self.get_all_instances_dict()
        relevant_event_config = configured_instances.get(data.EventID)
        if relevant_event_config is None:
            return {}
        relevant_fields = {}
        for var in all_variables.keys():
            matching_var = relevant_event_config.get(var)
            if matching_var is not None:
                relevant_fields[var] = {"value": all_variables[var], "config": matching_var.params}
        return relevant_fields
