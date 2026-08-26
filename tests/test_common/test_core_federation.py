from detectmatelibrary.common._core_op._fed_component import IncompatibleFed
from detectmatelibrary.common.core import CoreComponent

import struct

import pytest


class DummyComponent(CoreComponent):
    pass


class DummyComponent2(CoreComponent):
    pass


class TestJoinOp:
    def test_add(self) -> None:
        component1 = CoreComponent(name="comp_1")
        component2 = CoreComponent(name="comp_2")
        component3 = CoreComponent(name="comp_3")

        component2 + component3
        assert len(component2._components) == 2
        assert component3._components == component2._components

        component1 = component1 + component3
        assert len(component1._components) == 3
        assert component1._components == component2._components
        assert component1._components == component3._components

    def test_sub(self) -> None:
        component1 = CoreComponent(name="comp_1")
        component2 = CoreComponent(name="comp_2")
        component3 = CoreComponent(name="comp_3")

        (component1 + component2 + component3) - component3
        assert len(component2._components) == 2
        assert component1._components == component2._components
        assert component3._components == {component3}

    def test_incompatible(self) -> None:
        component1 = DummyComponent2(name="comp_1")
        component2 = DummyComponent(name="comp_2")

        with pytest.raises(IncompatibleFed):
            component1 + component2
        with pytest.raises(IncompatibleFed):
            component1 - component2

    def test_stack(self) -> None:
        component1 = CoreComponent(name="comp_1")
        component2 = CoreComponent(name="comp_2")
        component3 = CoreComponent(name="comp_3")
        component4 = CoreComponent(name="comp_4")

        component1.stack(component2)
        assert len(component1._components) == 2
        assert component1._components != component2._components

        component1.stack([component3, component4])
        assert len(component1._components) == 4


class DummyAppendList(CoreComponent):
    def __init__(
        self, elems: list[str], name: str = "test", *args, **kwargs
    ) -> None:
        super().__init__(name, *args, **kwargs)
        self.elems = elems

    def aggregate_strategy(self, components):
        final_list = []
        for component in components:
            final_list.extend(component.elems)

        final_list = list(set(final_list))
        for component in components:
            component.elems = final_list

    def to_binary(self):
        return struct.pack(f">{len(self.elems)}h", *self.elems)

    def from_binary(self, binary):
        num_ints = len(binary) // 2
        elems = list(struct.unpack(f">{num_ints}h", binary))
        return DummyAppendList(elems=elems)


class DummyAppendListEmpty(CoreComponent):
    def __init__(
        self, elems: list[str], name: str = "test", *args, **kwargs
    ) -> None:
        super().__init__(name, *args, **kwargs)
        self.elems = elems


class TestFedComponent:
    def test_basic_aggregation(self) -> None:
        comp1 = DummyAppendList(elems=[1, 2])
        comp2 = DummyAppendList(elems=[3, 4])

        comp1.aggregate()
        assert set(comp1.elems) == {1, 2}

        (comp1 + comp2).aggregate()
        assert set(comp1.elems) == {1, 2, 3, 4}

    def test_stack_basic_aggregation(self) -> None:
        comp1 = DummyAppendList(elems=[1, 2])
        comp2 = DummyAppendList(elems=[3, 4])
        comp3 = DummyAppendList(elems=[5])

        comp1.stack([comp2, comp3])
        comp1.aggregate(unstack=True)
        assert set(comp1.elems) == {1, 2, 3, 4, 5}
        assert len(comp1._components) == 1

        comp1.stack([comp2, comp3])
        comp1.aggregate(unstack=False)
        assert set(comp1.elems) == {1, 2, 3, 4, 5}
        assert len(comp1._components) == 3

    def test_sanity_check(self) -> None:
        comp1 = DummyAppendList(elems=[1, 2])
        comp2 = comp1.from_binary(comp1.to_binary())

        assert comp2.elems == [1, 2]

    def test_stack_binary_aggregation(self) -> None:
        comp1 = DummyAppendList(elems=[1, 2])
        comp2 = DummyAppendList(elems=[3, 4])
        comp3 = DummyAppendList(elems=[5])

        comp1.stack([comp2.to_binary(), comp3.to_binary()])
        comp1.aggregate(unstack=True)
        assert set(comp1.elems) == {1, 2, 3, 4, 5}

        comp1.stack([comp2.to_binary(), comp3.to_binary()])
        output = comp1.aggregate(unstack=True)
        assert set(comp1.elems) == {1, 2, 3, 4, 5}
        assert isinstance(output, bytes)

    def test_empty_feed_fields(self) -> None:
        comp1 = DummyAppendListEmpty(elems=[1, 2])
        comp2 = DummyAppendListEmpty(elems=[3, 4])
        comp3 = DummyAppendListEmpty(elems=[5])

        with pytest.warns(UserWarning):
            comp1.to_binary()

        with pytest.warns(UserWarning):
            comp1.from_binary(b"")

        with pytest.warns(UserWarning):
            comp1.aggregate_strategy({comp1, comp2, comp3})
