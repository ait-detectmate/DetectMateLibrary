# Auto Parser

The auto parser uses a brute-force strategy: it iterates through every log-type record in the internal dataset and chooses the regex and templates that best matches the provided logs.

Compared with Template Matcher approaches, its key benefit is that you don’t need to supply templates or regex formatting during initialization, which makes it more convenient for rapid deployments. Its main drawback is that it only performs well for log types that are already included in the internal dataset.

The built-in dataset of log types cannot be modified by users and currently supports: HDFS, BGL, Audit, Syslog, OpenVPN, DNSmasq, and Apache.

It wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Configuration

Auto parser parameters:

- `method_type` (string): identifier for the parser type (e.g., `"auto_parser"`).
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
