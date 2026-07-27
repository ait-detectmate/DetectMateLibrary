from detectmatelibrary.common.deeplearning_detector import (
    DeepLearningDetectorConfig, DeepLearningDetector
)

from detectmatelibrary.utils.deep_learning.logbert import LogBert


from typing import Any


class LogBertDetectorConfig(DeepLearningDetectorConfig):
    method_type: str = "logbert_detector"

    hyperparameters: list[tuple[str | dict[str, str] | list[str], ...]] = {  # type: ignore
        "Model": {
            "n_embed": 10,
            "hidden": 32,
            "num_heads": 2,
            "n_layers": 1,
            "dropout": 0.0,
            "max_len": 1000,
        },
        "Train": {
            "seed": 0,
            "batch_size": 256,
            "learning_rate": 0.01,
            "epochs": 10,
            "mask_per": 0.4,
            "alpha": 0.0,
            "patience": 3,
        },
        "Finetune": [
            ["Model", "hidden", [64, 128, 256]]
            ["Model", "n_layers", [1, 2, 3]]
            ["Train", "learning_rate", [0.002, 0.001, 0.005]]
        ]
    }


class LogBertDetector(DeepLearningDetector):
    def __init__(
        self,
        name: str = "LogBertDetector",
        config: LogBertDetectorConfig | dict[str, Any] = LogBertDetectorConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = LogBertDetectorConfig.from_dict(config, name)

        super().__init__(
            name=name, model_cls=LogBert, config=config 
        )