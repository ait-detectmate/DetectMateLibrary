
from abc import ABC, abstractmethod


class DeepModel(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def check_anomaly(self, seq: tuple[int], top_k: int) -> bool:
        pass

    @abstractmethod
    def train(self, seqs: list[tuple[int]], var_per: float) -> dict[str, float]:
        pass

    @abstractmethod
    def finetune(self, seqs: list[tuple[int]], var_per: float, epochs: int = 2) -> None:
        pass
