from collections import defaultdict
from typing import Optional, Dict, List, Union
from typing_extensions import Literal
from ..common.detector import CoreDetector, CoreDetectorConfig
from .. import schemas
from pydantic import BaseModel, Field

import numpy as np


class EventConfig(BaseModel):
    """Configuration for a specific event ID with its associated variables and
    log format variables."""

    eventId: Union[int, Literal["all"]] = Field(
        default="all", description="Event ID to filter on, either an integer or 'all'"
    )
    variables: Union[List[int], List[Literal["all"]]] = Field(
        default=["all"],
        description="Variable indices to filter on, either a list of integers or 'all'",
    )
    logFormatVariables: Union[List[str], List[Literal["all"]]] = Field(
        default=["all"],
        description="Log format variables to filter on, either a list of strings or 'all'",
    )

    class Config:
        extra = "forbid"


class RandomConfig(CoreDetectorConfig):
    """Configuration for RandomDetector with hierarchical event-based
    filtering."""

    event_configs: Dict[Union[int, Literal["all"]], List[EventConfig]] = defaultdict(
        list
    )

    def add_event_config(
        self,
        eventId: Optional[Union[int, Literal["all"]]] = None,
        variables: Optional[Union[List[int], List[Literal["all"]]]] = None,
        logFormatVariables: Optional[Union[List[str], List[Literal["all"]]]] = None,
    ) -> None:
        """Add configuration for a specific event ID."""
        eventId_ = eventId if eventId is not None else "all"
        if eventId_ not in self.event_configs:
            self.event_configs[eventId_] = []
        variables = variables if variables is not None else ["all"]
        logFormatVariables = (
            logFormatVariables if logFormatVariables is not None else ["all"]
        )
        event_config = EventConfig(
            eventId=eventId_, variables=variables, logFormatVariables=logFormatVariables
        )
        self.event_configs[eventId_].append(event_config)

    def get_event_configs(self, eventId: int) -> List[EventConfig]:
        """Retrieve configurations for a specific event ID."""
        return self.event_configs.get(eventId, []) + self.event_configs.get("all", [])

    def get_filtered_data_instances(self, data_raw):
        """Extract and return data for configured events and variables.

        Return None if the event is not configured.
        """

        # Check if this event ID is configured for processing
        event_id = data_raw.EventID
        event_configs = self.get_event_configs(event_id)
        if not event_configs:
            # return empty iterator
            return {}

        data_instances = defaultdict(dict)

        # Extract relevant log format variables
        for event_config in event_configs:

            configured_data = defaultdict(list)
            for var_name in event_config.logFormatVariables:
                if var_name in data_raw.logFormatVariables.keys():
                    configured_data[var_name].append(
                        data_raw.logFormatVariables[var_name]
                    )
                else:
                    # If no specific log format variables configured, use all
                    configured_data = dict(data_raw.logFormatVariables)
            # Extract relevant variables
            for var_idx in event_config.variables:
                if var_idx == "all":
                    configured_data = dict(enumerate(data_raw.variables))
                elif var_idx < len(data_raw.variables):
                    configured_data[var_idx].append(data_raw.variables[var_idx])
                else:
                    Warning(
                        f"Variable index {var_idx} out of range for event ID {event_id}. Skipping."
                    )
            data_instances[event_id].update(configured_data)
        return data_instances


class RandomDetector(CoreDetector):
    """Random Detector with hierarchical configuration support."""

    def __init__(
        self, name: str = "RandomDetector", config: RandomConfig = RandomConfig()
    ) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)

    def train(self, input_: List[schemas.ParserSchema] | schemas.ParserSchema) -> None:
        """Train the detector by learning known values from the input data."""
        return

    def detect(
        self,
        input_: List[schemas.ParserSchema] | schemas.ParserSchema,
        output_: schemas.DetectorSchema
    ) -> bool:
        """Detect new values in the input data.

        Only processes events and variables specified in the
        hierarchical configuration.
        """
        overall_score = 0.0
        alerts = {}
        data_instances = self.config.get_filtered_data_instances(input_)
        for i, (event_id, data) in enumerate(data_instances.items()):
            # randomly decide if anomaly or not
            print(data)
            if np.random.rand() < 0.5:
                # anomaly_detected = True
                score = 1.0
                alerts.update({str(data): str(score)})
            else:
                # anomaly_detected = False
                score = 0.0
            overall_score += score
        if overall_score > 0:
            output_.score = overall_score
            # Use update() method for protobuf map fields
            output_.alertsObtain.update(alerts)
            return True
        return False
