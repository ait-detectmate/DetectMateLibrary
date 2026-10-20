from detectmatelibrary.common.alert_aggregator import (
    CoreAlertAggregator,
    CoreAlertAggregatorConfig,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema
from detectmatelibrary.utils.data_buffer import BufferMode


class DensityClusteringAggregationConfig(CoreAlertAggregatorConfig):
    """
    Configuration for the DensityClusteringAggregation class.

    Parameters:
        buffer_size (int): The size of the buffer.
        buffer_mode (BufferMode): The mode of the buffer.
        delta (float): The threshold for the clustering.
    """

    method_type: str = "density_clustering_aggregator"
    buffer_size: int = 3
    buffer_mode: BufferMode = BufferMode.BATCH
    delta: float


class DensityClusteringAggregation(CoreAlertAggregator):
    """This class implements alert aggregation by density clustering. It is an abstract class that requires the implementation of 2 methods in subclasses:

    1. One has to implement either the single_metric or the metric function. The single_metric function computes the distance between 2 alerts, while the metric function computes the distance matrix between a list of alerts. If both functions are implemented, the metric function will be used.

    2. The discard_alert_fn function must be implemented to determine which alerts should no longer be considered for aggregation. To this end, after each aggregation step, the discard_alert_fn function is called with the list of relevant alerts. It should return a list of booleans indicating which alerts should be discarded (True) and which should be kept (False).

    Args:
        config (DensityClusteringAggregationConfig): The configuration for the aggregator.
        name (str): The name of the aggregator.

    Methods:
        single_metric(alert1: DetectorSchema, alert2: DetectorSchema) -> float: Computes the distance between 2 alerts. Must be implemented in a subclass.
        metric(alerts: list[DetectorSchema], return_last_rows: int = 0) -> list[list[float]]: Computes the distance matrix between a list of alerts. Can be implemented in a subclass. If both single_metric and metric are implemented, the metric function will be used. The return_last_rows parameter can be used to compute only the last rows of the distance matrix.
        discard_alert_fn(alerts: list[DetectorSchema]) -> list[bool]: Determines which alerts should no longer be considered for aggregation. Must be implemented in a subclass.
        aggregate_alerts(input_: list[DetectorSchema], output_: AggregateSchema): Aggregates the input alerts and writes the results to the output.
    """

    def __init__(
        self,
        config: DensityClusteringAggregationConfig,
        name: str = "DensityClusteringAggregator",
    ) -> None:
        self.buffer_size = config.buffer_size
        self.buffer_mode = config.buffer_mode
        super().__init__(
            name=name,
            config=config,
            buffer_size=config.buffer_size,
            buffer_mode=config.buffer_mode,
        )
        self.next_group_id: int = 0
        self.relevant_alerts: list[DetectorSchema] = []
        self.alert_id_to_group_id: dict[str, int | None] = {}
        self.active_groups: dict[int, set[int]] = {}
        self.message_buffer: list[str] = []
        self.description = "Alert aggregation by density clustering."

    def single_metric(
        self, alert1: DetectorSchema, alert2: DetectorSchema
    ) -> float:
        raise NotImplementedError(
            "The metric function must be implemented in a subclass of DensityClusteringAggregation."
        )

    def metric(
        self, alerts: list[DetectorSchema], return_last_rows: int = 0
    ) -> list[list[float]]:
        return [
            [self.single_metric(alert1, alert2) for alert2 in alerts]
            for alert1 in alerts[-return_last_rows:]
        ]

    def discard_alert_fn(self, alerts: list[DetectorSchema]) -> list[bool]:
        raise NotImplementedError(
            "The discard_alert_fn function must be implemented in a subclass of DensityClusteringAggregation."
        )

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:

        if not isinstance(input_, list):
            input_ = [input_]

        # identify new alerts and add them to relevant alerts
        new_alerts = self._add_new_alerts(input_)

        # check distance of new alerts to relevant alerts
        is_same_group = self._check_threshold(
            self.metric(
                self.relevant_alerts,
                len(new_alerts),
            )
        )

        # assign groups to new alerts and merge groups if necessary
        for new_alert, same_group in zip(new_alerts, is_same_group, strict=True):
            self._assign_new_alert_to_group(new_alert, same_group)

        # write results to output
        self._write_output(input_, output_)
        return True

    def _write_output(
        self, input_: list[DetectorSchema], output_: AggregateSchema
    ) -> None:
        output_["description"] = self.description
        output_["alertsObtain"].update(
            {
                alert["alertID"]: str(self.alert_id_to_group_id[alert["alertID"]])
                for alert in input_
            }
        )

        # discard alerts that are no longer relevant
        _, affected_group_ids = self._discard_alerts()
        self._check_and_discard_group_ids(affected_group_ids)
        output_["alertsObtain"]["messages"] = "\n".join(self.message_buffer)
        self.message_buffer = []

    def _add_new_alerts(self, input_: list[DetectorSchema]) -> list[DetectorSchema]:
        new_input = [
            alert
            for alert in input_
            if alert["alertID"] not in self.alert_id_to_group_id
        ]
        self.relevant_alerts.extend(new_input)
        self.alert_id_to_group_id.update(
            {alert["alertID"]: None for alert in new_input}
        )
        return new_input

    def _check_threshold(
        self, distance_matrix: list[list[float]]
    ) -> list[list[bool]]:
        return [
            [distance <= self.config.delta for distance in row]
            for row in distance_matrix
        ]

    def _new_group(self, alert_id: int) -> int:
        group_id = self.next_group_id
        self.alert_id_to_group_id[alert_id] = group_id
        self.active_groups[group_id] = {group_id}
        self.next_group_id += 1
        return group_id

    def _check_and_merge_groups(self, close_group_ids: set[int]) -> set[int] | None:
        # check if groups are merged already
        groups_to_merge = []
        for group_id in close_group_ids:
            if (full_group := self.active_groups[group_id]) not in groups_to_merge:
                groups_to_merge.append(full_group)

        if (num_groups := len(groups_to_merge)) == 0:
            raise Exception("An error occurred while merging groups!")
        elif num_groups == 1:
            # all groups are merged already
            return

        # merge groups
        new_group = set.union(*groups_to_merge)
        for group_id in new_group:
            self.active_groups[group_id] = new_group

        self.message_buffer.append(
            f"Groups {groups_to_merge} are merged into {new_group}."
        )
        return new_group

    def _assign_new_alert_to_group(
        self, new_alert: DetectorSchema, close_relevant_alerts: list[bool]
    ) -> None:
        close_alerts = [
            relevant_alert
            for relevant_alert, is_close in zip(
                self.relevant_alerts, close_relevant_alerts, strict=True
            )
            if is_close
        ]

        if len(close_alerts) == 0:
            raise Exception("Alert is not close to itself!")

        elif len(close_alerts) == 1:
            # only close alert is itself, create new group
            assert close_alerts[0]["alertID"] == new_alert["alertID"]
            self._new_group(new_alert["alertID"])
            return

        # check distinct groups of close alerts
        close_group_ids = {
            self.alert_id_to_group_id[alert["alertID"]] for alert in close_alerts
        }

        if len(close_group_ids) == 0:
            raise Exception("Could not find group_id's of close alerts!")

        elif len(close_group_ids) == 1:
            if (group_id := close_group_ids.pop()) is None:
                # all close alerts are not assigned to a group, create new group
                self._new_group(new_alert["alertID"])
                return

            # all close alerts belong to the same group, assign new alert to that group
            self.alert_id_to_group_id[new_alert["alertID"]] = group_id
            return

        # unlabelled close alerts can be ignored now, they will be labelled in their own iteration
        close_group_ids.discard(None)
        close_group_ids: set[int] = close_group_ids

        # close alerts have multiple group_ids, add alert to some group_id
        for group_id in close_group_ids:
            self.alert_id_to_group_id[new_alert["alertID"]] = group_id
            break

        # merge groups if necessary
        self._check_and_merge_groups(close_group_ids)

    def _discard_alerts(self, keep_buffer: bool = True) -> tuple[list[int], set[int]]:
        alerts_to_discard = self.discard_alert_fn(self.relevant_alerts)
        if keep_buffer and self.buffer_mode == BufferMode.WINDOW:
            # set the last self.buffer_size elements of alerts_to_discard to False
            for i in range(1, self.buffer_size + 1):
                if i > len(alerts_to_discard):
                    break
                alerts_to_discard[-i] = False
        discarded_alert_ids = [
            alert["alertID"]
            for alert, discard in zip(
                self.relevant_alerts, alerts_to_discard, strict=True
            )
            if discard
        ]
        affected_group_ids = {
            group_id
            for group_id in (
                self.alert_id_to_group_id.pop(alert_id)
                for alert_id in discarded_alert_ids
            )
        }
        self.relevant_alerts = [
            alert
            for alert, discard in zip(
                self.relevant_alerts, alerts_to_discard, strict=True
            )
            if not discard
        ]
        return discarded_alert_ids, affected_group_ids

    def _check_and_discard_group_ids(self, group_ids_to_check: set[int]) -> None:
        # remove groups that are unreachable anymore
        group_ids_to_discard = {
            group_id
            for group_id in group_ids_to_check
            if group_id not in self.alert_id_to_group_id.values()
        }
        for group_id in group_ids_to_discard:
            self.message_buffer.append(f"Group id {group_id} is finished.")

            # check if group_id has been merged with still active groups
            full_group_to_check = self.active_groups.pop(group_id)
            for group_id_to_check in full_group_to_check:
                if group_id_to_check in self.active_groups:
                    break
            else:
                # full_group_to_check is not reachable anymore
                self.message_buffer.append(f"Group {full_group_to_check} is finished.")
