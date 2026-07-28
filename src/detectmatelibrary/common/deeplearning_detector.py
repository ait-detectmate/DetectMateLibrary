
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary.utils.data_buffer import BufferMode

from detectmatelibrary import schemas


class DeepLearningDetectorConfig(CoreDetectorConfig):
    window_size: int = 10
    validation_per: float = 0.2
    finetune_epochs: int = 2

    hyperparameters: list[tuple[str | dict[str, str] | list[str], ...]] = {  # type: ignore
        "Model": {

        },
        "Train": {

        },
        "Finetune": [],
    }


def build_seq(input_: list[schemas.ParserSchema]) -> tuple[int]:
    return tuple([in_["EventID"] for in_ in input_])


class DeepLearningDetector(CoreDetector):
    def __init__(
        self,
        model_cls: DeepModel,
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

    def set_configuration(self) -> None:
        self.model.finetune(
            self.config_seqs, var_per=self.config.validation_per, epochs=self.config.finetune_epochs
        )
        self.config_seqs = []

    def post_train(self) -> None:
        self.stats = self.model.train(self.train_seqs, var_per=self.config.validation_per)
        self.train_seqs = []

        if "top_k" in self.stats:
            self.top_k = int(self.stats["top_k"])
            print(self.model)
            print("Top k assigned", self.top_k)

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
