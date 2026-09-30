from detectmatelibrary.common.deeplearning_detector import (
    DeepLearningDetectorConfig, DeepLearningDetector
)

from detectmatelibrary.utils.deep_learning.deeplog import DeepLog


from typing import Any
from pydantic import Field


class DeeplogDetectorConfig(DeepLearningDetectorConfig):
    method_type: str = Field(
        default="deeplog_detector", description="Indicates what type of method it is."
    )

    hyperparameters: dict[str, Any] = Field(
        default={
            "Model": {
                "hidden_dim": 64,
                "n_layers": 2,
            },
            "Train": {
                "seed": 0,
                "batch_size": 2048,
                "learning_rate": 0.01,
                "epochs": 10,
                "patience": 3,
            },
            "Finetune": [
                ["Model", "hidden_dim", [128, 256, 512]],
                ["Model", "n_layers", [1, 2, 3]],
                ["Train", "learning_rate", [0.01, 0.02, 0.03]],
            ],
        },
        description="Model, training and hyperparameter-search settings for the DeepLog model.",
    )


class DeeplogDetector(DeepLearningDetector):
    def __init__(
        self,
        name: str = "DeeplogDetector",
        config: DeeplogDetectorConfig | dict[str, Any] = DeeplogDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = DeeplogDetectorConfig.from_dict(config, name)

        super().__init__(
            name=name, model_cls=DeepLog, config=config 
        )