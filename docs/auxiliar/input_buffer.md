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
--8<-- "docs/examples/others/data_buffer.py:example_1"
```

### Batch mode

```python
--8<-- "docs/examples/others/data_buffer.py:example_2"
```

### Window mode

```python
--8<-- "docs/examples/others/data_buffer.py:example_3"
```

Go back [Index](../index.md)
