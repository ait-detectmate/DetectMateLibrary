
# --8<-- [start:example_1]
from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode

results = []
buf = DataBuffer(ArgsBuffer(mode=BufferMode.NO_BUF, process_function=results.append))
buf.add(1)
buf.add(2)

print(results)  # [1, 2]
# --8<-- [end:example_1]


# --8<-- [start:example_2]
results = []
buf = DataBuffer(ArgsBuffer(mode=BufferMode.BATCH, process_function=results.append, size=3))

buf.add(1)
print(results)  # []

buf.add(1)
print(results)  # []

buf.add(1)
print(results)  # [[1, 1, 1]]

# --8<-- [end:example_2]


# --8<-- [start:example_3]
buf = DataBuffer(ArgsBuffer(mode=BufferMode.WINDOW, process_function=sum, size=2))

print(buf.add(1) is None)  # True
print(buf.add(2))  # 3
print(buf.add(5))  # 7
# --8<-- [end:example_3]
