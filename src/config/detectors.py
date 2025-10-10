"""Detector configuration classes."""

from __future__ import annotations
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import warnings
import re


class DetectorVariable(BaseModel):
    id: int
    name: Optional[str] = None
    params: Optional[dict] = None


class HeaderVariable(BaseModel):
    # Note: YAML uses string IDs in header-variables (e.g., Level, Time)
    id: str
    params: Optional[dict] = None


class DetectorInstance(BaseModel):
    id: str
    event: Union[int, Literal["all"]]
    template: Optional[str] = None
    variables: Optional[List[DetectorVariable]] = None
    header_variables: Optional[List[HeaderVariable]] = Field(
        default=None,
        alias="header-variables",
        description="Header-derived variables kept separate for clarity.",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("event")
    @classmethod
    def _non_negative_event(cls, v):
        if isinstance(v, int) and v < 0:
            raise ValueError("event must be >= 0 or 'all'")
        return v

    @model_validator(mode="after")
    def _warn_on_out_of_range_variable_ids(self):
        """If a template is provided, count occurrences of '<*>' and warn when
        a variable.id falls outside that range (as your example suggests)."""
        if self.template and self.variables:
            # Count "<*>" occurrences very literally:
            m = re.findall(r"<\*>", self.template)
            slot_count = len(m)
            for var in self.variables:
                if var.id < 0:
                    warnings.warn(
                        f"[{self.id}] Variable id {var.id} is negative; it will be ignored.",
                        stacklevel=2,
                    )
                elif slot_count and var.id >= slot_count:
                    warnings.warn(
                        f"[{self.id}] Variable id {var.id} out of range for template with {slot_count} "
                        f"slots; will be ignored.",
                        stacklevel=2,
                    )
        return self


class DetectorConfig(BaseModel):
    """Generic detector config; allows extra fields to support detector-
    specific settings.

    - ExampleDetector: requires 'parser' reference and 'instances' unless auto_config=true.
    - AnotherDetector: may have auto_config=true and accept other fields.
    """

    type: str
    parser: Optional[str] = Field(
        default=None,
        description="If present, must reference a ParserInstance.id.",
    )
    auto_config: bool = False
    instances: Optional[List[DetectorInstance]] = None

    # Let detector-specific fields through without failing:
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _instances_required_if_not_auto(self):
        if not self.auto_config and (
            self.instances is None or len(self.instances) == 0
        ):
            raise ValueError(
                f"Detector '{self.type}' has auto_config=false, but no explicit instances were provided."
            )
        return self
