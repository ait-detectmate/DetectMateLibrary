# Drain parser

The parsed is based in the official [Drain publication](https://ieeexplore.ieee.org/document/8029742).

This parser wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. Prefer  use the performance implementation when parsing many log lines in non-stream (batch) mode.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

WARNING: This parser is not yet in a stable release and may behave differently across platforms or hardware.

## Configuration

Drain parser arguments:

- `method_type` (string): parser type identifier (for example `"tree_matcher"`).
- `depth` (int): Number of word layers.
- `max_childs` (int): max number of childs allow in the length layer.
- `sim_thres` (float): similarity threshold.
- `reset_in_post_train` (bool): if true remove the logs in the train buffer when the templates are generated. Otherwise, it safe them for the next train.
- `auto_config` (bool): whether to attempt an optional auto-configuration phase (not required).

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
