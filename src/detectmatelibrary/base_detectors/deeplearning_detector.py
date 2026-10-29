
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary import schemas

from typing import Any
from pydantic import Field
import numpy as np
import logging


class DeepLearningDetectorConfig(CoreDetectorConfig):
    window_size: int = Field(
        default=10,
        description="Number of consecutive events used as one training/detection sequence.",
    )
    validation_per: float = Field(
        default=0.2,
        description="Fraction of data held out for validation during (fine)training.",
    )
    finetune_epochs: int = Field(
        default=2,
        description="Number of epochs used when finetuning during the configuration phase.",
    )
    train_sample: float = Field(
        default=1.0,
        gt=0.0,
        le=1.0,
        description=(
            "Fraction of the collected sequences the model finetunes and trains on: a seeded "
            "random sample, kept in log order, rounded down to at least one sequence. "
            "1.0 uses every sequence."
        ),
    )
    train_sample_seed: int = Field(
        default=0,
        description="Seed of the train_sample draw, so reruns use the same sequences.",
    )

    hyperparameters: dict[str, Any] = Field(
        default={
            "Model": {

            },
            "Train": {

            },
            "Finetune": [],
        },
        description=(
            "Model, training and hyperparameter-search settings passed to "
            "the underlying deep learning model."
        ),
    )


def build_seq(input_: list[schemas.ParserSchema]) -> tuple[int]:
    return tuple([in_["eventID"] for in_ in input_])


def sample_seqs(seqs: list[tuple[int]], share: float, seed: int) -> list[tuple[int]]:
    """Keep a seeded random ``share`` of the sequences, in log order.

    The count is rounded down, but at least one sequence is kept.
    ``share`` 1.0 returns ``seqs`` itself.
    """
    if share >= 1.0 or not seqs:
        return seqs

    n_keep = max(1, int(share * len(seqs)))
    keep = np.sort(np.random.default_rng(seed).choice(len(seqs), size=n_keep, replace=False))
    logging.info(f"train_sample {share}: keeping {n_keep} of {len(seqs)} sequences")
    return [seqs[i] for i in keep]


class DeepLearningDetector(CoreDetector):
    def __init__(
        self,
        model_cls: DeepModel,
        name: str = "CoreDetector",
        config: DeepLearningDetectorConfig | dict[str, Any] = DeepLearningDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DeepLearningDetectorConfig.from_dict(config, name)

        super().__init__(
            name=name,
            buffer_mode=BufferMode.WINDOW,
            buffer_size=config.window_size,
            config=config
        )
        self.config: DeepLearningDetectorConfig
        self.model: DeepModel = model_cls(config=self.config.hyperparameters)  # type: ignore

        self.train_seqs: list[tuple[int]] = []
        self.config_seqs: list[tuple[int]] = []
        self.stats: dict[str, float | int] = {}
        self.top_k: int = 0

    def train(self, input_: list[schemas.ParserSchema]) -> None:  # type: ignore
        self.train_seqs.append(build_seq(input_))

    def configure(self, input_: list[schemas.ParserSchema]) -> None:  # type: ignore
        self.config_seqs.append(build_seq(input_))

    def _sample(self, seqs: list[tuple[int]]) -> list[tuple[int]]:
        return sample_seqs(seqs, share=self.config.train_sample, seed=self.config.train_sample_seed)

    def set_configuration(self) -> None:
        self.model.finetune(
            self._sample(self.config_seqs),
            var_per=self.config.validation_per,
            epochs=self.config.finetune_epochs,
        )
        self.config_seqs = []

    def post_train(self) -> None:
        self.stats = self.model.train(self._sample(self.train_seqs), var_per=self.config.validation_per)
        self.train_seqs = []

        if "top_k" in self.stats:
            self.top_k = int(self.stats["top_k"])
            logging.info(self.model)
            logging.info(f"Top k assigned {self.top_k}")

    def detect(
        self,
        input_: list[schemas.ParserSchema],  # type: ignore
        output_: schemas.DetectorSchema,
    ) -> bool:

        alert = self.model.check_anomaly(build_seq(input_), top_k=self.top_k)
        if alert:
            output_["score"] = 1.0
            output_["description"] = f"{self.name} found an anomaly in the sequence"
            return True

        return False
