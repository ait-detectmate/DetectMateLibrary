from detectmatelibrary.common.deeplearning_detector import (
    DeepLearningDetectorConfig, DeepLearningDetector
)

from detectmatelibrary.utils.deep_learning.deeplog import DeepLog


from typing import Any


class DeeplogDetectorConfig(DeepLearningDetectorConfig):
    method_type: str = "deeplog_detector"

    hyperparameters: list[tuple[str | dict[str, str] | list[str], ...]] = {  # type: ignore
        "Model": {
            "hidden_dim": 64,
            "n_layers": 2,
        },
        "Train": {
            "batch_size": 2048,
            "learning_rate": 0.01,
            "epochs": 10,
        },
        "finetune": [
            ["Model", "hidden_dim", [128, 256, 512]]
            ["Model", "n_layers", [1, 2, 3]]
            ["Train", "learning_rate", [0.01, 0.02, 0.03]]
        ],
    }


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