
import warnings
from typing import Self, overload


class IncompabtibleFed(Exception):
    def __init__(self) -> None:
        super().__init__("Instances are incompatible")


class _CompOp:
    @staticmethod
    def is_compatible(main_inst: object, other_inst: object) -> None:
        if not isinstance(other_inst, type(main_inst)):
            raise IncompabtibleFed()

    @staticmethod
    def reset(main_inst: object, attr: str) -> None:
        main_inst.__setattr__(attr, {main_inst})

    @staticmethod
    def combine(main_inst: object, attr: str, other_inst: object) -> None:
        _CompOp.is_compatible(main_inst, other_inst)
        set_main: set[object] = getattr(main_inst, attr)

        set_main.update(getattr(other_inst, attr))
        for elem in set_main:
            getattr(elem, attr).update(set_main)

    @staticmethod
    def uncombine(main_inst: object, attr: str, other_inst: object) -> None:
        _CompOp.is_compatible(main_inst, other_inst)
        set_main: set[object] = getattr(main_inst, attr)

        for elem in list(set_main):
            if elem == other_inst:
                _CompOp.reset(other_inst, attr)
            else:
                elem._components.remove(other_inst)  # type: ignore

    @staticmethod
    def stack(main_inst: object, attr: str, list_other_inst: list[object]) -> None:
        set_main: set[object] = getattr(main_inst, attr)
        for other_inst in list_other_inst:
            _CompOp.is_compatible(main_inst, other_inst)
            set_main.add(other_inst)


class FedOperations:
    __COMPONENT: str = "_components"

    def __init__(self) -> None:
        self._components: set["FedOperations"]
        _CompOp.reset(self, self.__COMPONENT)

    def __add__(self, other: object) -> Self:
        _CompOp.combine(self, attr=self.__COMPONENT, other_inst=other)

        return self

    def __sub__(self, other: object) -> Self:
        _CompOp.uncombine(self, attr=self.__COMPONENT, other_inst=other)

        return self

    @overload
    def stack(self, other: bytes | list[bytes]) -> None:
        pass

    @overload
    def stack(self, other: object | list[object]) -> None:
        pass

    def stack(self, other: object | list[object | bytes] | bytes) -> None:
        if not isinstance(other, list):
            other = [other]
        _CompOp.stack(
            self, attr=self.__COMPONENT, list_other_inst=[
                self.from_binary(inst) if isinstance(inst, bytes) else inst for inst in other
            ]
        )

    def aggregate(self, unstack: bool = False) -> None | bytes:
        self.aggregate_strategy(self._components)

        if unstack:
            _CompOp.reset(self, self.__COMPONENT)

        return self.to_binary()

    def to_binary(self) -> bytes | None:
        warnings.warn("To binary not implemented, return None")
        return None

    def from_binary(self, binary: bytes) -> object:
        warnings.warn(f"To binary not implemented, return None for {binary!r}")
        return None

    def aggregate_strategy(self, components: set["FedOperations"]) -> None:
        warnings.warn(f"No strategy found, aggregations does nothing for {components}")
