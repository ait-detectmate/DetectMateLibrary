
# --8<-- [start:example_1]
from detectmatelibrary.common.core import CoreComponent
import struct


class NewComponent(CoreComponent):  # Inherent from CoreComponent
    def __init__(self, elems):
        self.elems = elems
        super().__init__(name="FedExample")

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
        return NewComponent(elems=elems)


# --8<-- [end:example_1]
# --8<-- [start:example_2]
detector1 = NewComponent([1, 2, 3])
detector2 = NewComponent([4, 5])
detector3 = NewComponent([6])

detector1 + detector2 + detector3

detector2.aggregate()  # Detector 2 is used as centralize node

print("Dectector 3", detector3.elems)  # All detectors have been updated

# --8<-- [end:example_2]

# --8<-- [start:example_3]
detector1 = NewComponent([1, 2, 3])
detector2 = NewComponent([4, 5])
detector3 = NewComponent([6])

detector1 + detector2 + detector3

detector2.aggregate()  # Detector 2 is used as centralize node

print("Dectector 3", detector3.elems)  # All detectors have been updated
# --8<-- [end:example_3]

# --8<-- [start:example_4]
detector1 = NewComponent([1, 2, 3])
detector2 = NewComponent([4, 5])
detector3 = NewComponent([6])

detector1.stack([detector2, detector3])

detector2.aggregate()
print("Detector 3", detector3.elems)  # It is not longer combine but stack, so it will not work

detector1.aggregate()
print("Detector 3", detector3.elems)  # Now it will work

# --8<-- [end:example_4]

# --8<-- [start:example_5]
detector1 = NewComponent([1, 2, 3])

binary2 = NewComponent([4, 5]).to_binary()
binary3 = (detector3 := NewComponent([6])).to_binary()
print("Binary of Detector 3", binary3)

detector1.stack([binary2, binary3])
output = detector1.aggregate(unstack=True)  # unstack = True will free memory

print("Detector 1", detector1.elems)  # Detector 1 has been updated
print("Output binary", output)  # Output that we send to other componets

# We update detector 3 now
print("Detector 3", detector3.elems)  # Now detector 3 is not in the share memory so it will not work
detector3 = detector3.from_binary(output)
print("Detector 3", detector3.elems)  # Now it will work
# --8<-- [end:example_5]
