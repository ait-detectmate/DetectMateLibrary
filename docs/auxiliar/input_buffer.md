# Data Buffer [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/utils/data_buffer.py)]

Components use the data buffer to process streaming input one item at a time, in batches, or in sliding windows.

| Type   | State   | Description |
|--------|---------|-------------|
| **No buffer** | BufferMode.NO_BUF | Returns one value at a time. |
| **Batch** | BufferMode.BATCH | Returns values in batches. |
| **Window** | BufferMode.WINDOW | Returns values in sliding windows. |


## Examples

These examples show how `DataBuffer` works in each mode.

### No Buffer mode
```python title="No Buffer"
--8<-- "docs/examples/others/data_buffer.py:example_1"
```

### Batch mode

```python title="Batch Mode"
--8<-- "docs/examples/others/data_buffer.py:example_2"
```

### Window mode

```python title="Windows Mode"
--8<-- "docs/examples/others/data_buffer.py:example_3"
```
