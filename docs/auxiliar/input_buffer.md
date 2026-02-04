#  Data Buffer

The data buffer is an auxiliar methods that can be use in all the components. It takes the stream data and formated to the specifications given.

It has different configuration states to configure its behaviour.

| Type   | State   | Description |
|--------|---------|-------------|
| **No buffer** | BufferMode.NO_BUF | Returns one value at the time. |
| **Batch** | BufferMode.BATCH | Returns values by batches.|
| **Window**| BufferMode.WINDOW | Returns values by time windows. |


## Examples

Code examples to show the behaviour of the **DataBuffer** class.

### No Buffer mode
```python
from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode

results = []
buf = DataBuffer(ArgsBuffer(mode=BufferMode.NO_BUF, process_function=results.append))
buf.add(1)
buf.add(2)

print(results)  # [1, 2]

```

### Batch mode

```python
from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode

results = []
buf = DataBuffer(ArgsBuffer(mode=BufferMode.BATCH, process_function=results.append, size=3))

buf.add(1)
print(results)  # []

buf.add(1)
print(results)  # []

buf.add(1)
print(results)  # [[1, 1, 1]]
```

### Window mode

```python
from detectmatelibrary.utils.data_buffer import DataBuffer, ArgsBuffer, BufferMode

buf = DataBuffer(ArgsBuffer(mode=BufferMode.WINDOW, process_function=sum, size=2))

print(buf.add(1) is None)  # True
print(buf.add(2))  # 3
print(buf.add(5))  # 7
```

Go back [Index](../index.md)
