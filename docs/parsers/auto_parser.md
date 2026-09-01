# Auto Parser

Parse the logs using the templates saved in the dataset. (HDFS, BGL, Audit, SysLog, Apache, OpenVPN, Thunderbird).

It wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. When parsing large numbers of log lines in non-stream (batch) mode, it is recommended to use the performance-oriented implementation.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Configuration

Auto parser parameters:

- `method_type` (string): identifier for the parser type (e.g., `"aut_parser"`).
- `fix_type` (str): fix type of logs to process.


## Usage example

Without fixing log type:

```python
--8<-- "docs/examples/parsers/auto_parser.py:example_1"
```

With fixing log type:

```python
--8<-- "docs/examples/parsers/auto_parser.py:example_2"
```

Go back to [Index](../index.md)
