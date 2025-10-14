from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, field_serializer
from typing import List, Optional, Union, Literal
import warnings
import re

from components.common.core import CoreComponent, CoreConfig

from utils.data_buffer import ArgsBuffer
from utils.aux import get_timestamp

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

    @model_validator(mode="after")
    def _calculate_n_instances(self):
        """Calculate total number of variables across all instances."""
        self._n_instances = 0
        if self.instances:
            for i in self.instances:
                instance = (
                    i
                    if isinstance(i, DetectorInstance)
                    else DetectorInstance.model_validate(i)
                )
                self._n_instances += len(getattr(instance, "variables") or [])
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
            self._calculate_n_instances()
        return self._n_instances

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
        self._calculate_n_instances()


def _extract_timestamp(
    input_: List[schemas.ParserSchema] | schemas.ParserSchema,
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [int(i.logFormatVariables["timestamp"]) for i in input_]


def _extract_logIDs(
    input_: List[schemas.ParserSchema] | schemas.ParserSchema,
) -> List[int]:
    if not isinstance(input_, list):
        input_ = [input_]

    return [i.logID for i in input_]


class CoreDetector(CoreComponent):
    def __init__(
        self,
        name: str = "CoreDetector",
        buffer_mode: Optional[Literal["no_buf", "batch", "window"]] = "no_buf",
        buffer_size: Optional[int] = None,
        config: Optional[CoreDetectorConfig | dict] = CoreDetectorConfig(),
    ):
        if isinstance(config, dict):
            config = CoreDetectorConfig.from_dict(config)

        super().__init__(
            name=name,
            type_="Detector",
            config=config,
            args_buffer=ArgsBuffer(mode=buffer_mode, size=buffer_size),
            input_schema=schemas.PARSER_SCHEMA,
            output_schema=schemas.DETECTOR_SCHEMA,
        )

    def run(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema,
    ) -> bool:

        output_.logIDs.extend(_extract_logIDs(input_))
        output_.extractedTimestamps.extend(_extract_timestamp(input_))
        output_.alertID = self.id_generator()
        output_.receivedTimestamp = get_timestamp()

        anomaly_detected = self.detect(input_=input_, output_=output_)
        output_.detectionTimestamp = get_timestamp()

        return True if anomaly_detected is None else anomaly_detected

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema,
    ) -> bool | None:
        return True

    def train(
        self, input_: schemas.ParserSchema | list[schemas.ParserSchema]
    ) -> None: ...
