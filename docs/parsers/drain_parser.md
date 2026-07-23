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
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary import schemas

# instantiate parser (config can be a dict or a config object)
config_dict = {
    "parsers": {
        "DrainParser": {
            "method_type": "drain_parser",
            "data_use_training": 2,
            "reset_in_post_train": False,
        }
    }
}

parser = DrainParser(config=config_dict)

parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "hello there <*> kenobi"

parser.update_state("keep_training")
parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
parser.update_state("stop_training")

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "hello there <*> kenobi"
```

Simple usage (Reset = True):

```python
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary import schemas

# instantiate parser (config can be a dict or a config object)
config_dict = {
    "parsers": {
        "DrainParser": {
            "method_type": "drain_parser",
            "data_use_training": 2,
            "reset_in_post_train": False,
        }
    }
}

parser = DrainParser(config=config_dict)

parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
print(parsed["template"])  # "templates not yet generated"

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "hello there <*> kenobi"

parser.update_state("keep_training")
parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
parser.update_state("stop_training")

parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
print(parsed["template"])  # "template not found"
```

Go back to [Index](../index.md)
