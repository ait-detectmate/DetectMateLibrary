# Drain parser

The parser is derived from the official [Drain publication](https://ieeexplore.ieee.org/document/8029742).

It also wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. When parsing large numbers of log lines in non-stream (batch) mode, it is recommended to use the performance-oriented implementation.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Configuration

Drain parser parameters:

- `method_type` (string): identifier for the parser type (e.g., `"tree_matcher"`).
- `depth` (int): number of token/word levels.
- `max_childs` (int): maximum number of children allowed in the given layer.
- `sim_thres` (float): threshold used for similarity.
- `reset_in_post_train` (bool): if enabled, clears logs from the training buffer once templates are created; otherwise, it keeps them for the next training cycle.
- `auto_config` (bool): indicates whether to run an optional auto-configuration step (not mandatory).

Example YAML fragment:
```yaml
parsers:
  DrainParser:
    method_type: drain_parser
    auto_config: False
    params:
      depth: 2
```

## Usage example

Simple usage (Reset = False):

```python
--8<-- "docs/examples/parsers/drain_parser.py:example_1"
```

Simple usage (Reset = True):

```python
--8<-- "docs/examples/parsers/drain_parser.py:example_2"
```

Go back to [Index](../index.md)
