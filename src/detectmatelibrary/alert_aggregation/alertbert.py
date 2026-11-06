from collections.abc import Callable
from datetime import datetime as dt
from typing import Any, Literal, cast

from pydantic import Field, NonNegativeFloat

from detectmatelibrary.base_alert_aggregation import (
    DensityClusteringAggregation,
    DensityClusteringAggregationConfig,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema
from detectmatelibrary.tools.logging import logger
from detectmatelibrary.utils.alertbert.datasets import AlertDataset, split_alert_dataset
from detectmatelibrary.utils.alertbert.models import (
    AlertBERT,
    MaskedLanguageModel,
)
from detectmatelibrary.utils.data_buffer import BufferMode


class AlertBERTAggregationConfig(DensityClusteringAggregationConfig):
    """Configuration of the AlertBERTAggregation class.

    Besides the parameters of the alert aggregation this configuration
    also determines the training of the masked-languge-model used to
    obtain the alert embeddings.
    """
    # general
    method_type: str = Field(
        default="AlertBERTAggregation",
        description="The type of the aggregation method. Defaults to 'AlertBERT_aggregator'.",
    )
    _model_id: str = f"{method_type}_{dt.now().isoformat()}"
    model_id: str = Field(
        default=_model_id,
        description="""The unique identifier of the model.
            Defaults to 'AlertBERT_aggregator_<current_datetime>'.""",
    )
    path: str = Field(
        default="alertbert_models",
        description="The path to the save location of the AlertBERT model. Defaults to 'alertbert_models'.",
    )
    train_model: bool = Field(
        default=True,
        description="""Whether to train the AlertBERT model.
            If False, the model will be loaded from disk.
            Defaults to False.""",
    )
    save_model: bool = Field(
        default=True,
        description="""Whether to save the trained AlertBERT model to disk.
            Defaults to True.""",
    )

    # aggregation
    delta: NonNegativeFloat = Field(
        default=10.0,
        description="The threshold for the clustering. Defaults to 10.0."
    )
    theta: NonNegativeFloat = Field(
        default=20.0,
        description="The parameter for the time-cosine-distance. Defaults to 20.0.",
    )
    dim_reduction: int = Field(
        default=2,
        description="""The dimension to which the alert embeddings will be reduced via PCA before clustering.
            Defaults to 2."""
    )
    clustering_backend: Literal["detectmate", "scipy"] = Field(
        default="detectmate",
        description="""The backend to use for clustering.
            The option "detectmate" uses the implementation inherited from the parent class,
            the option "scipy" uses the implementation of the AlertBERT model.
            Defaults to "detectmate".""",
    )
    layers: tuple[str] | tuple[str, str] = Field(
        default=("embedding", "encoder"),
        description="""The layers of the AlertBERT model to use for obtaining the alert embeddings.
            Defaults to ("embedding", "encoder").""",
    )
    buffer_size: int = Field(
        default=1000,
        description="The size of the buffer. Defaults to 1000."
    )
    buffer_mode: BufferMode = Field(
        default=BufferMode.BATCH,
        description="The mode of the buffer. Defaults to 'BATCH'.",
    )

    # data
    train_size: int = Field(
        default=50000,
        description="The number of alerts to use for training the AlertBERT model. Defaults to 50000."
    )
    val_size: int = Field(
        default=10000,
        description="""The number of alerts to use for validation during training of the AlertBERT model.
            Defaults to 10000."""
    )
    skip_first: int = Field(
        default=0,
        description="""The number of alerts to skip before starting to collect alerts for training the
            AlertBERT model.
            Defaults to 0."""
    )
    min_freq: int = Field(
        default=10,
        description="""The minimum frequency of tokens to be included in the
            vocabulary of the AlertBERT model.
            Defaults to 10.""",
    )

    # model
    features: tuple[str, ...] = Field(
        default=("description",),
        description="""The keys of fields of the alerts to use as features for training the AlertBERT model.
            Fields within the 'alertDetails' field can be accessed by the syntax 'alertDetails:fieldName'.
            Defaults to ("description",).""",
    )
    encoding: Literal["index", "relevantTimestamp"] = Field(
        default="relevantTimestamp",
        description="""The features of the alerts to use for rotary positional encoding.
            Defaults to "relevantTimestamp".""",
    )
    n_heads: int = Field(
        default=4,
        description="The number of attention heads in the AlertBERT model. Defaults to 4."
    )
    dim_per_head: int = Field(
        default=16,
        description="The dimensionality of each attention head in the AlertBERT model. Defaults to 16.",
    )
    num_layers: int = Field(
        default=1,
        description="The number of layers in the model in the AlertBERT model. Defaults to 1."
    )
    feedforward_factor: int = Field(
        default=4,
        description="""The factor by which the feedforward dimension is larger than the model dimension
            in the AlertBERT model. Defaults to 4.""",
    )
    rotary_max_exp: int = Field(
        default=14,
        description="""The maximum exponent for the rotary positional encoding in the AlertBERT model.
            Defaults to 14.""",
    )
    rotary_cutoff: float = Field(
        default=0.75,
        description="""The cutoff for the rotary positional encoding in the AlertBERT model.
            Defaults to 0.75.""",
    )

    # training
    context_size: int = Field(
        default=1024,
        description="The context size for the AlertBERT model. Defaults to 1024."
    )
    batch_size: int = Field(
        default=8,
        description="The batch size for training the AlertBERT model. Defaults to 8."
    )
    updates: tuple[int, int] = Field(
        default=(240, 300),
        description="The number of updates for training the AlertBERT model. Defaults to (240, 300).",
    )
    lr: float = Field(
        default=5e-3,
        description="The learning rate for training the AlertBERT model. Defaults to 5e-3.",
    )
    warm_up_steps: int = Field(
        default=20,
        description="The number of warm-up steps for training the AlertBERT model. Defaults to 100."
    )

    def _get_mlm_config(self) -> dict[str, Any]:
        return self.model_dump(
            exclude={
                "buffer_mode",
                "params",
                "component_type",
                "auto_config",
                "start_id",
                "data_use_training",
                "data_use_configure",
                "use_config_data_as_training",
                "buffer_size",
                "delta",
                "theta",
                "dim_reduciton",
                "clustering_backend",
                "layers",
            }
        )


class AlertBERTAggregation(DensityClusteringAggregation):
    """Alert Aggregation based on alert timestamps and embeddings obtained from masked-language-models as
    proposed by [AlertBERT: A noise-robust alert grouping framework for simultaneous cyber attacks]
    (https://arxiv.org/abs/2602.06534).
    The alerts will be assigned to the same group if their time-cosine-distance is below a
    certain threshold theta.
    The time-cosine-distance is the maximum of the time difference and the cosine similarity between
    the embeddings of each alert.
    """

    def __init__(
        self,
        name: str = "AlertBERTAggregation",
        config: AlertBERTAggregationConfig = AlertBERTAggregationConfig(),
    ) -> None:
        """Initialize the AlertBERTAggregation class.

        Args:
            config (AlertBERTAggregationConfig): The configuration of this method.
            name (str): The name identifying this aggregation method.
        """
        if isinstance(config, dict):
            config = AlertBERTAggregationConfig.from_dict(config, name)
        super().__init__(name=name, config=config)
        self.config: AlertBERTAggregationConfig  # ty: ignore[invalid-mutable-override]
        self.description = "Alert aggregation by the AlertBERT method."
        self._set_up_mlm()
        if self.config.train_model:
            self.collected_data: list[DetectorSchema] = []
        self.timestamp_extraction_fn: Callable[[DetectorSchema], float] = lambda alert: (
            float(alert["logTimestamps"][-1])
        )
        self.last_timestamp: float = 0.0

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:
        """Aggregate alerts into groups using the AlertBERT method. If the
        model is set to be trained, it will first collect enough alerts to
        train the model, and then proceed with the aggregation. If the model is
        already trained, it will directly aggregate the alerts using the
        specified clustering backend.

        Args:
            input_ (list[DetectorSchema] | DetectorSchema): The alerts to aggregate.
            output_ (AggregateSchema): The output schema to populate.

        Returns:
            bool: True if the alerts were aggregated, False otherwise.
        """
        if not isinstance(input_, list):
            input_ = [input_]
        if self.timestamp_extraction_fn(input_[0]) < self.last_timestamp:
            raise ValueError("Alerts must be given in order of their timestamps!")
        else:
            self.last_timestamp = self.timestamp_extraction_fn(input_[-1])

        if self.config.train_model:
            self.collected_data.extend(input_)
            if (
                len(self.collected_data)
                >= self.config.skip_first
                + self.config.train_size
                + self.config.val_size
            ):
                logger.info("Data collection complete.")
                self._train_mlm()
                del self.collected_data
                logger.info("Proceeding with alert aggregation ...")
                self.last_timestamp = 0.0
                return self.aggregate_alerts(input_, output_)
            else:
                return False
        else:
            if self.config.clustering_backend == "detectmate":
                return super().aggregate_alerts(input_, output_)
            elif self.config.clustering_backend == "scipy":
                return self._aggregate_alerts(input_, output_)
            else:
                raise ValueError(
                    f"Clustering backend '{self.config.clustering_backend}' is not supported."
                )

    def _aggregate_alerts(
        self, input_: list[DetectorSchema], output_: AggregateSchema
    ) -> bool:
        """Aggregate alerts into groups using the AlertBERT method with the
        scipy backend.

        Args:
            input_ (list[DetectorSchema]): The alerts to aggregate.
            output_ (AggregateSchema): The output schema to populate.

        Returns:
            bool: True if the alerts were aggregated, False otherwise.
        """
        self._add_new_alerts(input_)
        labels = self.alertbert(self.relevant_alerts)

        # keep track of which labels belong to which group_id's
        label_to_group_id: dict[int, int] = {}

        # first map labels to groups
        # then assign new alerts to groups
        for alert, label in zip(self.relevant_alerts, labels, strict=True):
            # old alerts have group_id's already
            if (
                current_group_id := self.alert_id_to_group_id[alert["alertID"]]
            ) is not None:
                # check which group_id the labels belong to and merge them if the labels say so
                if label not in label_to_group_id:
                    label_to_group_id[label] = current_group_id
                else:
                    other_group_id = label_to_group_id[label]
                    if other_group_id != current_group_id:
                        self._check_and_merge_groups({other_group_id, current_group_id})
            # new alerts have no group_id's yet, assign them to the group of the label
            else:
                # a new label requires creating an new group
                if label not in label_to_group_id:
                    group_id = self._new_group(alert["alertID"])
                    label_to_group_id[label] = group_id
                # otherwise assign the new alert to the group of the label
                else:
                    self.alert_id_to_group_id[alert["alertID"]] = label_to_group_id[
                        label
                    ]

        # write results to output
        self._write_output(input_, output_)
        return True

    def metric(
        self,
        alerts: list[DetectorSchema],
        return_last_rows: int = 0,
    ) -> list[list[NonNegativeFloat]]:
        """Compute the time-cosine-distance between the embeddings of the
        alerts.

        Args:
            alerts (list[DetectorSchema]): The alerts for which to compute the metric.
            return_last_rows (int): The number of last rows to return. Defaults to 0.

        Returns:
            list[list[NonNegativeFloat]]: The time-cosine-distances between the embeddings of the alerts.
        """
        alert_emb = self.alertbert._get_embeddings(alerts)
        return cast(
            list[list[NonNegativeFloat]],
            self.alertbert.time_cosine_metric(
                alert_emb[-return_last_rows:], alert_emb
            ).tolist(),
        )

    def discard_alert_fn(self, alerts: list[DetectorSchema]) -> list[bool]:
        """Determine which alerts should be discarded based on their
        timestamps.

        Args:
            alerts (list[DetectorSchema]): The alerts to check for discarding.

        Returns:
            list[bool]: A list of booleans indicating whether each alert should be discarded.
        """
        cutoff = self.relevant_alerts[-1]["logTimestamps"][-1] - self.config.delta
        return [alert["logTimestamps"][-1] < cutoff for alert in alerts]

    def _set_up_mlm(self) -> None:
        """Set up the MaskedLanguageModel."""
        self.mlm = MaskedLanguageModel(self.config)
        if not self.config.train_model:
            logger.info("AlertBERT model loaded from disk.")
            self._set_up_alertbert()
        else:
            logger.info("AlertBERT model will be trained ...")

    def _set_up_alertbert(self) -> None:
        """Set up the AlertBERT model."""
        self.alertbert = AlertBERT(
            model=self.mlm,
            config=self.config,
        )
        logger.info("AlertBERT model setup complete.")

    def _train_mlm(
        self,
        use_gathered_alerts: bool = True,
        train_data: AlertDataset | None = None,
        val_data: AlertDataset | None = None,
    ) -> None:
        """Train the MaskedLanguageModel.

        Args:
            use_gathered_alerts (bool): Whether to use the gathered alerts for training. Defaults to True.
            train_data (AlertDataset | None): The training dataset. Required if use_gathered_alerts is False.
            val_data (AlertDataset | None): The validation dataset. Required if use_gathered_alerts is False.
        Raises:
            ValueError: If use_gathered_alerts is False and train_data or val_data is None.
        """
        if use_gathered_alerts:
            train_plus_val_size = self.config.train_size + self.config.val_size
            train_split = self.config.train_size / train_plus_val_size
            val_split = self.config.val_size / train_plus_val_size
            train_data, val_data, _ = split_alert_dataset(
                AlertDataset(
                    self.collected_data[self.config.skip_first:],
                ),
                train_val_test_split=(train_split, val_split, 0.0),
            )
        else:
            if train_data is None or val_data is None:
                raise ValueError(
                    "train_data and val_data must be provided if use_gathered_alerts is False."
                )
        logger.info("Training AlertBERT model ...")
        self.mlm.fit(train_data, val_data)
        self.config.train_model = False
        logger.info("AlertBERT model training complete.")
        self._set_up_alertbert()
        if self.config.train_model:
            raise ValueError("The model should not be trained after training!")
