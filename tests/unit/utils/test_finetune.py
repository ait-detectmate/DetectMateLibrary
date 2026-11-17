
from detectmatelibrary.utils.finetune import Combinations

from detectmatelibrary.common.core import CoreConfig

from typing import Any
import pytest


class DummyConfig(CoreConfig):
    a: int = 2
    b: int = 10
    c: float = 0.2

    Finetune: list[tuple[str, list[Any]]] = [
        ["a", [1, 2, 3, 4]],
        ["b", [10, 40]],
        ["c", [0.2, 0.4, 0.6, 0.8]]
    ]


class DummyConfig2(CoreConfig):
    a: int = 2
    b: int = 10
    c: float = 0.4


class DummyConfig3(CoreConfig):
    a: int = 2
    b: int = 10

    Finetune: list[tuple[str, list[Any]]] = [
        ["a", [1, 2, 3, 4]],
        ["b", [10, 40]],
        ["c", [0.2, 0.4, 0.6, 0.8]]
    ]


hyperparameters_without = {
    "Model": {
        "a": 1,
    },
    "Train": {
        "b": 2,
    },
}


hyperparameters = {
    "Model": {
        "a": 1,
    },
    "Train": {
        "b": 2,
    },
    "Finetune": [
        ["Model", "a", [1, 2, 3, 4]],
        ["Train", "b", [10, 40]],
        ["c", [0.2, 0.4, 0.6, 0.8]]
    ]
}


class TestCombinations:
    def test_combination_no_overwrite(self):
        comb = Combinations(config := DummyConfig())
        assert config != next(comb())

    def test_call_format(self):
        comb = Combinations(DummyConfig())
        config = next(comb())

        assert config.a == 1
        assert config.b == 10
        assert config.c == 0.2

    def test_get_best(self):
        comb = Combinations(DummyConfig())
        for j, _ in enumerate(comb()):
            comb.add_value(j)

        best_config = comb.get_best()
        assert best_config.a == 1
        assert best_config.b == 10
        assert best_config.c == 0.2

    def test_finetune_not_found(self):
        with pytest.warns(UserWarning):
            comb = Combinations(DummyConfig2())

        for _ in comb():
            assert False
        config = comb.get_best()

        assert config.a == 2
        assert config.b == 10
        assert config.c == 0.4

    def test_argument_missing(self):
        comb = Combinations(DummyConfig3())

        for j, _ in enumerate(comb()):
            comb.add_value(j)
        config = comb.get_best()

        assert config.a == 1
        assert config.b == 10

    def test_compatibility_dl_without(self):
        with pytest.warns(UserWarning):
            comb = Combinations(hyperparameters_without)

        for j, _ in enumerate(comb()):
            comb.add_value(j)
        config = comb.get_best()

        assert config["Model"]["a"] == 1
        assert config["Train"]["b"] == 2

    def test_compatibility_with_dl(self):
        comb = Combinations(hyperparameters)

        for j, _ in enumerate(comb()):
            comb.add_value(j)
        config = comb.get_best()

        print(comb.paths)
        assert config["Model"]["a"] == 1
        assert config["Train"]["b"] == 10
