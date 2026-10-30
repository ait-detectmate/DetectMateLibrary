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
    """Configuration of the AlertBERTAggregation class. Besides the parameters
    of the alert aggregation this configuration also determines the training of
    the masked-languge-model used to obtain the alert embeddings.

    Args:
        path (str): The path to the save location of the AlertBERT model. Defaults to 'alertbert_models'.
        train_model (bool): Whether to train the AlertBERT model.
            If False, the model will be loaded from disk. Defaults to False.
        delta (NonNegativeFloat): The threshold for the clustering. Defaults to 10.0
        theta (NonNegativeFloat): The parameter for the time-cosine-distance. Defaults to 20.0
        dim_reduction (int): The dimension to which the alert embeddings will be reduced via
            PCA before clustering. Defaults to 2.
        clustering_backend (Literal["detectmate", "scipy"]): The backend to use for clustering.
            The option "detectmate" uses the implementation inherited from the parent class, the option
            "scipy" uses the implementation of the AlertBERT model. Defaults to "detectmate".
        layers (tuple[Literal["embedding", "encoder"]]): The layers of the AlertBERT model to use for
            obtaining the alert embeddings. Defaults to ("embedding", "encoder").
        buffer_size (int): The size of the buffer. Defaults to 1000.
        buffer_mode (BufferMode): The mode of the buffer. Defaults to BufferMode.BATCH.
        train_size (int): The number of alerts to use for training the AlertBERT model. Defaults to 10000.
        val_size (int): The number of alerts to use for validation during training of the AlertBERT model.
            Defaults to 1000.
        skip_first (int): The number of alerts to skip before starting to collect alerts for
            training the AlertBERT model. Defaults to 0.
        min_freq (int): The minimum frequency of tokens to be included in the
            vocabulary of the AlertBERT model. Defaults to 10.
        features (tuple[str, ...]): The keys of fields of the alerts to use as features for training the
            AlertBERT model. Defaults to ("description",).
        encoding (Literal["index", "relevantTimestamp"]): The features of the alerts to use for rotary
            positional encoding in the AlertBERT model. Defaults to "relevantTimestamp".
        n_heads (int): The number of attention heads in the AlertBERT model. Defaults to 4.
        dim_per_head (int): The dimension of each attention head in the AlertBERT model. Defaults to 16.
        num_layers (int): The number of layers in the AlertBERT model. Defaults to 1.
        feedforward_factor (int): The factor by which the feedforward dimension is larger than the model
            dimension in the AlertBERT model. Defaults to 4.
        rotary_max_exp (int): The maximum exponent for the rotary embeddings in the AlertBERT model.
            Defaults to 14.
        rotary_cutoff (float): The cutoff exponent for the frequencies of the rotary embeddings in the
            AlertBERT model. Defaults to 0.75.
        context_size (int): The context size for the AlertBERT model. Defaults to 1024.
        batch_size (int): The batch size for training the AlertBERT model. Defaults to 8.
        updates (tuple[int, int]): The number of updates for training the AlertBERT model.
            Defaults to (1800, 2000).
        lr (float): The learning rate for training the AlertBERT model. Defaults to 5e-3.
        warm_up_steps (int): The number of warm-up steps for training the AlertBERT model. Defaults to 100.
    """

    # general
    method_type: str = Field(
        default="AlertBERT_aggregator",
        description="The type of the aggregation method.",
    )
    path: str = Field(
        default="alertbert_models", description="The path to the AlertBERT models."
    )
    model_id: str = f"{method_type}_{dt.now().isoformat()}"
    train_model: bool = Field(
        default=False, description="Whether to train the AlertBERT model."
    )

    # aggregation
    delta: NonNegativeFloat = 10.0
    theta: NonNegativeFloat = 20.0
    dim_reduction: int = 2
    clustering_backend: Literal["detectmate", "scipy"] = "detectmate"
    layers: tuple[str] | tuple[str, str] = ("embedding", "encoder")
    buffer_size: int = 1000
    buffer_mode: BufferMode = BufferMode.BATCH

    # data
    train_size: int = 10000
    val_size: int = 1000
    skip_first: int = 0
    min_freq: int = 10

    # model
    features: tuple[str, ...] = ("descritption",)
    encoding: Literal["index", "relevantTimestamp"] = "relevantTimestamp"
    n_heads: int = 4
    dim_per_head: int = 16
    num_layers: int = 1
    feedforward_factor: int = 4
    rotary_max_exp: int = 14
    rotary_cutoff: float = 0.75

    # training
    context_size: int = 1024
    batch_size: int = 8
    updates: tuple[int, int] = (1800, 2000)
    lr: float = 5e-3
    warm_up_steps: int = 100

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

    Args:
        config (AlertBERTAggregationConfig): The configuration of this method.
        name (str): The name identifying this aggregation method.
    """

    def __init__(
        self,
        config: AlertBERTAggregationConfig,
        name: str = "AlertBERTAggregator",
    ) -> None:
        super().__init__(name=name, config=config)
        self.config: AlertBERTAggregationConfig  # ty: ignore[invalid-mutable-override]
        self.description = "Alert aggregation by the AlertBERT method."
        self._set_up_mlm()
        if self.config.train_model:
            self.collected_data: list[DetectorSchema] = []

    def aggregate_alerts(
        self, input_: list[DetectorSchema] | DetectorSchema, output_: AggregateSchema
    ) -> bool:
        if not isinstance(input_, list):
            input_ = [input_]
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
                    f"Clustering backend '{self.config['clustering_backend']}' is not supported."
                )

    def _aggregate_alerts(
        self, input_: list[DetectorSchema], output_: AggregateSchema
    ) -> bool:
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
        alert_emb = self.alertbert._get_embeddings(alerts)
        return cast(
            list[list[NonNegativeFloat]],
            self.alertbert.time_cosine_metric(
                alert_emb[-return_last_rows:], alert_emb
            ).tolist(),
        )

    def discard_alert_fn(self, alerts: list[DetectorSchema]) -> list[bool]:
        cutoff = self.relevant_alerts[-1]["extractedTimestamps"][-1] - self.config.delta
        return [alert["extractedTimestamps"][-1] < cutoff for alert in alerts]

    def _set_up_mlm(self) -> None:
        self.mlm = MaskedLanguageModel(self.config)
        if not self.config.train_model:
            logger.info("AlertBERT model loaded from disk.")
            self._set_up_alertbert()
        else:
            logger.info("AlertBERT model will be trained ...")

    def _set_up_alertbert(self) -> None:
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
        try:
            self.mlm.fit(train_data, val_data)
            self.config.train_model = False
        except Exception as e:
            logger.error(f"Error during AlertBERT model training: {e}")
            return
        logger.info("AlertBERT model training complete.")
        self._set_up_alertbert()
        if not self.config.train_model:
            raise ValueError(
                "The model should not be trained after training!"
            )
