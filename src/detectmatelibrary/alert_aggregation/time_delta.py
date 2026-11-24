from collections.abc import Callable
from typing import Any

from pydantic import Field, NonNegativeFloat

from detectmatelibrary.base_alert_aggregation.density_clustering import (
    DensityClusteringAggregation,
    DensityClusteringAggregationConfig,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema


class TimeDeltaAggregationConfig(DensityClusteringAggregationConfig):
    """Configuration of the TimeDeltaAggregation class.

    Args:
        delta (NonNegativeFloat): The time threshold below which two alerts are allocated to the same group.
    """

    method_type: str = Field(
        default="time_delta_aggregator",
        description="The kind of aggregation method.",
    )
    delta: NonNegativeFloat = Field(
        default=10.0, description="The threshold for the clustering."
    )


class TimeDeltaAggregation(DensityClusteringAggregation):
    """This class implements alert aggregation by the time-delta method introduced by
    [Landauer et al.](https://doi.org/10.1145/3510581).
    Two alerts will be assigned to the same group if the time difference
    between them is below a certain threshold delta.
    The time difference is computed based on the timestamps of the last logs associated
    with each alert as these determine the earliest time at which the alert was detected.
    Important: It is assumed that the alerts arrive in order of their timestamps!
    """

    def __init__(
        self,
        config: TimeDeltaAggregationConfig | dict[str, Any] = TimeDeltaAggregationConfig(),
        name: str = "TimeDeltaAggregator",
    ) -> None:
        """Initialize the TimeDeltaAggregation class.

        Args:
            name (str): The name identifying this aggregation method.
            config (TimeDeltaAggregationConfig): The configuration of this method.
        """
        if isinstance(config, dict):
            config = TimeDeltaAggregationConfig.from_dict(config, name)

        super().__init__(name=name, config=config)
        self.timestamp_extraction_fn: Callable[[DetectorSchema], float] = lambda alert: (
            float(alert["logTimestamps"][-1])
        )
        self.description = "Alert aggregation by the time-delta method."
        self.last_timestamp: float = 0.0

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:
        """Aggregate input alerts and write the results to the output.

        Args:
            input_: The alert or alerts to aggregate.
            output_: The schema to which aggregation results are written.

        Returns:
            ``True`` after the aggregation results have been written.
            ``False`` if no new alerts were aggregated and the output schema was not modified.
        """

        if not isinstance(input_, list):
            input_ = [input_]

        if self.timestamp_extraction_fn(input_[0]) < self.last_timestamp:
            raise ValueError("Alerts must be aggregated in order of their timestamps!")
        else:
            self.last_timestamp = self.timestamp_extraction_fn(input_[-1])

        return super().aggregate_alerts(input_, output_)

    def single_metric(
        self,
        alert1: DetectorSchema,
        alert2: DetectorSchema,
    ) -> NonNegativeFloat:
        """Compute the time difference between two alerts.

        Args:
            alert1 (DetectorSchema): The first alert.
            alert2 (DetectorSchema): The second alert.
        Returns:
            NonNegativeFloat: The time difference between the two alerts.
        """
        return abs(
            self.timestamp_extraction_fn(alert1) - self.timestamp_extraction_fn(alert2)
        )

    def discard_alert_fn(self, alerts: list[DetectorSchema]) -> list[bool]:
        """Discards all but the last alert in a list of alerts as this is the
        only one relevant for the time-delta method.

        Args:
            alerts (list[DetectorSchema]): The list of alerts to discard from.

        Returns:
            list[bool]: A list of booleans indicating which alerts to discard.
        """
        return [i + 1 != len(alerts) for i in range(len(alerts))]
