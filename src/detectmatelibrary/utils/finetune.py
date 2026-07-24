from detectmatelibrary.common.core import CoreConfig

from typing import Any
import numpy as np

import itertools
import warnings
import typing
import copy


class Combinations:
    def __init__(self, config: CoreConfig) -> None:
        self.config = config

        self.paths: list[str] = []
        self.combs: list[tuple[Any, ...]] = []
        if "finetune" not in dir(config):
            warnings.warn("No finetune options found")
        else:
            self.paths = [path[0] for path in getattr(config, "finetune")]
            self.combs = list(itertools.product(
                *[path[-1] for path in getattr(config, "finetune")]
            ))
        self.values: list[float] = []

    def add_value(self, value: float) -> None:
        self.values.append(value)

    def get_best(self) -> CoreConfig:
        if self.values == []:
            return self.config

        idx = np.argmin(self.values)
        for i, combo in enumerate(self.combs):
            if i == idx:
                config = copy.deepcopy(self.config)
                for path, value in zip(self.paths, combo):
                    if path in dir(self.config):
                        setattr(config, path, value)
                return config
        return self.config

    def __call__(self) -> typing.Iterable[CoreConfig]:
        for combo in self.combs:
            config = copy.deepcopy(self.config)
            for path, value in zip(self.paths, combo):
                if path in dir(config):
                    setattr(config, path, value)

            yield config
