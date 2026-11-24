
from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig

from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary.utils.deep_learning._op import PAD
from detectmatelibrary.utils.data_buffer import ArgsBuffer, BufferMode, DataBuffer

from detectmatelibrary import schemas

from typing import Any
from pydantic import Field
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
    session_variable: str | None = Field(
        default=None,
        description=(
            "Header variable that names the session of each event (HDFS: block_id). When set, "
            "an event's window holds the events before it in its own session, padded at the "
            "session start, so windows never mix sessions and every event is checked."
        ),
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


def build_seq(input_: list[schemas.ParserSchema]) -> tuple[int, ...]:
    return tuple([in_["eventID"] for in_ in input_])


class SessionWindows:
    """The window ending at the latest event of each session, padded with PAD
    at its start."""

    def __init__(self, size: int) -> None:
        self.size = size
        self.windows: dict[str, tuple[int, ...]] = {}

    def add(self, session: str, event: int) -> tuple[int, ...]:
        """Add ``event`` to ``session`` and return the session's window ending
        at it."""
        window = self.windows.get(session, (PAD,) * self.size)[1:] + (event,)
        self.windows[session] = window
        return window


class DeepLearningDetector(CoreDetector):
    def __init__(
        self,
        model_cls: DeepModel,
        name: str = "CoreDetector",
        config: DeepLearningDetectorConfig | dict[str, Any] = DeepLearningDetectorConfig()
    ) -> None:

        if isinstance(config, dict):
            config = DeepLearningDetectorConfig.from_dict(config, name)

        by_session = config.session_variable is not None
        super().__init__(
            name=name,
            buffer_mode=BufferMode.NO_BUF if by_session else BufferMode.WINDOW,
            buffer_size=None if by_session else config.window_size,
            config=config
        )
        self.config: DeepLearningDetectorConfig
        self.model: DeepModel = model_cls(config=self.config.hyperparameters)  # type: ignore

        self.train_seqs: list[tuple[int, ...]] = []
        self.config_seqs: list[tuple[int, ...]] = []
        self.stats: dict[str, float | int] = {}
        self.top_k: int = 0

        # With sessions, configure() and train() each keep their own windows: train() also
        # gets the configure records, replayed after the configure phase. detect() does not
        # get them, so its windows are built where every record passes once, the buffer.
        self.config_windows = SessionWindows(self.config.window_size)
        self.train_windows = SessionWindows(self.config.window_size)
        self.detect_windows = SessionWindows(self.config.window_size)
        self.window: tuple[int, ...] = ()
        if by_session:
            self.args_buffer = ArgsBuffer(BufferMode.NO_BUF, process_function=self._add_to_session)
            self.data_buffer = DataBuffer(self.args_buffer)

    def _session(self, input_: schemas.ParserSchema) -> str:
        session = input_["headerVariables"].get(self.config.session_variable)
        if session is None:
            raise ValueError(f"<<{self.name}>> log has no header variable {self.config.session_variable!r}")
        return str(session)

    def _add_to_session(self, input_: schemas.ParserSchema) -> schemas.ParserSchema:
        self.window = self.detect_windows.add(self._session(input_), input_["eventID"])
        return input_

    def _seq(
        self, input_: list[schemas.ParserSchema] | schemas.ParserSchema, windows: SessionWindows
    ) -> tuple[int, ...]:
        if self.config.session_variable is None:
            return build_seq(input_)  # type: ignore
        return windows.add(self._session(input_), input_["eventID"])  # type: ignore

    def train(self, input_: list[schemas.ParserSchema]) -> None:  # type: ignore
        self.train_seqs.append(self._seq(input_, self.train_windows))

    def configure(self, input_: list[schemas.ParserSchema]) -> None:  # type: ignore
        self.config_seqs.append(self._seq(input_, self.config_windows))

    def set_configuration(self) -> None:
        self.model.finetune(
            self.config_seqs, var_per=self.config.validation_per, epochs=self.config.finetune_epochs
        )
        self.config_seqs = []
        self.config_windows = SessionWindows(self.config.window_size)

    def post_train(self) -> None:
        self.stats = self.model.train(self.train_seqs, var_per=self.config.validation_per)
        self.train_seqs = []
        self.train_windows = SessionWindows(self.config.window_size)

        if "top_k" in self.stats:
            self.top_k = int(self.stats["top_k"])
            logging.info(self.model)
            logging.info(f"Top k assigned {self.top_k}")

    def detect(
        self,
        input_: list[schemas.ParserSchema],  # type: ignore
        output_: schemas.DetectorSchema,
    ) -> bool:

        seq = build_seq(input_) if self.config.session_variable is None else self.window
        alert = self.model.check_anomaly(seq, top_k=self.top_k)
        if alert:
            output_["score"] = 1.0
            output_["description"] = f"{self.name} found an anomaly in the sequence"
            return True

        return False
