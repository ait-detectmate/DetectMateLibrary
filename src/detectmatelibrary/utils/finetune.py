from detectmatelibrary.common.core import CoreConfig

from typing import Any
import numpy as np

import itertools
import warnings
import typing
import copy


class CombOp:
    @staticmethod
    def is_finetune_in_there(config: CoreConfig | dict[str, Any]) -> bool:
        variables = dir(config) if isinstance(config, CoreConfig) else config
        return "finetune" in variables

    @staticmethod
    def get_value(config: CoreConfig | dict[str, Any], path: str) -> Any:
        return getattr(config, path) if isinstance(config, CoreConfig) else config[path]

    @staticmethod
    def set_value(config: CoreConfig | dict[str, Any], path: list[str], value: Any) -> None:
        if isinstance(config, CoreConfig):
            setattr(config, path[0], value)
        else:
            path = [path] if isinstance(path, str) else path
            dict_ = config
            for v in path[:-1]:
                dict_ = dict_[v]

            dict_[path[-1]] = value

    @staticmethod
    def value_exist(config: CoreConfig | dict[str, Any], path: list[str]) -> bool:
        if isinstance(config, CoreConfig):
            return path[0] in dir(config)

        path = [path] if isinstance(path, str) else path
        dict_ = config
        for v in path[:-1]:
            dict_ = dict_[v]

        return path[-1] in dict_


class Combinations:
    def __init__(self, config: CoreConfig | dict[str, Any]) -> None:
        self.config = config

        self.paths: list[list[str]] = []
        self.combs: list[tuple[Any, ...]] = []
        if not CombOp.is_finetune_in_there(config):
            warnings.warn("No finetune options found")
        else:
            self.paths = [path[:-1] for path in CombOp.get_value(config, "finetune")]
            self.combs = list(itertools.product(
                *[path[-1] for path in CombOp.get_value(config, "finetune")]
            ))
        self.values: list[float] = []

    def add_value(self, value: float) -> None:
        self.values.append(value)

    def get_best(self) -> CoreConfig | dict[str, Any]:
        if self.values == []:
            return self.config

        idx = np.argmin(self.values)
        for i, combo in enumerate(self.combs):
            if i == idx:
                config = copy.deepcopy(self.config)
                for path, value in zip(self.paths, combo):
                    if CombOp.value_exist(config, path):
                        CombOp.set_value(config, path, value)
                return config
        return self.config

    def __call__(self) -> typing.Iterable[CoreConfig | dict[str, Any]]:
        for combo in self.combs:
            config = copy.deepcopy(self.config)
            for path, value in zip(self.paths, combo):
                if CombOp.value_exist(config, path):
                    CombOp.set_value(config, path, value)

            yield config
