
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.utils.data_buffer import BufferMode


class DeepLearningDetectorConfig(CoreDetectorConfig):
    window_size: int = 10
    hyperparameters: list[tuple[str | dict[str, str], ...]] = {  # type: ignore
        "Model": {

        },
        "Train": {

        },
        "finetune": {

        },
    }


class DeepLearningDetector(CoreDetector):
    def __init__(
        self,
        name: str = "CoreDetector",
        config: DeepLearningDetectorConfig = DeepLearningDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DeepLearningDetectorConfig.from_dict(config, name)

        super().__init__(
            name=name,
            buffer_mode=BufferMode.WINDOW,
            buffer_size=config.window_size,
            config=config
        )
