# Parsers [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/common/parser.py)]

Parsers convert unstructured raw logs into structured ParserSchema objects that downstream detectors consume.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](schemas.md)    | Unstructured log   |
| **Output** | [ParserSchema](schemas.md) | Structured log     |

This document explains expected APIs, how to implement a parser, testing tips and common pitfalls.

## Overview

- Parsers must inherit from `CoreParser` and provide a `parse()` implementation.
- `CoreParser.run()` handles lifecycle and calls `parse()` for each input; implement pure parsing logic inside `parse()` where possible.
- Use a typed `Config` class (subclass of `CoreParserConfig`) to hold runtime parameters.

## CoreParser: minimal API

Recommended signatures and behavior:

```python title="Parser main methods"
class CoreParser:
    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        """Top-level runner. Calls parse() and performs pre/post processing.
        Return True when a parsed output was produced, False otherwise.
        """

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool | None:
        """Implement parsing here.
        - Fill the required output_ fields (see "ParserSchema: what to populate" below).
        - Return True, or None, to emit output_ as the parsed log.
        - Return False to drop the log: process() then returns None for it.
        """

    def train(self, input_: schemas.LogSchema) -> None:
        """Optional: train internal models. Can be a no-op for stateless parsers."""
```

## ParserSchema: what to populate

`parse()` only has to fill the fields that describe the match:

- `eventID` (int): identifier for the matched template/event
- `template` (string): event template text
- `variables` (repeated string): extracted parameters (extend the list)

`CoreParser.run()`, which calls `parse()`, fills in everything else for you:

- `parserID`, `parserType`: the parser's name and `method_type`
- `parsedLogID`: a new unique ID for the parsed record
- `logID`, `log`: copied from the input `LogSchema`
- `headerVariables`: the header fields extracted with `log_format`
- `receivedTimestamp`, `parsedTimestamp`: set just before and just after
  `parse()` runs

Don't set these in `parse()`: `run()` writes `parsedTimestamp` after `parse()`
returns, so a value set there is overwritten.

## Creating a new parser: step by step

1. Create a Config class inheriting `CoreParserConfig`.
2. Create parser class inheriting `CoreParser`.
3. Implement `parse()` to populate `output_`.
4. Add unit tests for `parse()` behavior.

Example:

```python title="Example of a Dummy parser"
# filepath: src/detectmatelibrary/parsers/my_parser.py
from typing import Any

from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas


class MyParserConfig(CoreParserConfig):
    method_type: str = "my_parser"
    # add parser-specific settings here
    pattern: str | None = None


class MyParser(CoreParser):
    def __init__(
        self,
        name: str = "MyParser",
        config: MyParserConfig | dict[str, Any] = MyParserConfig(),
    ):
        if isinstance(config, dict):
            config = MyParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        text = input_.log or ""
        # simple example: split on whitespace and treat as variables
        tokens = text.split()
        output_["eventID"] = 1
        output_["template"] = " ".join(["<*>"] * len(tokens))
        output_["variables"].extend(tokens)
        return True
```

## Testing parsers

Test `parse()` directly with a `LogSchema` input and a `ParserSchema` output.

```python title="Testing parser"
from detectmatelibrary.parsers.my_parser import MyParser
from detectmatelibrary import schemas


def test_my_parser_parse():
    parser = MyParser()
    raw = schemas.LogSchema({"log": "a b c", "logID": "1"})
    out = schemas.ParserSchema()
    ok = parser.parse(raw, out)
    assert ok is True
    assert out["eventID"] == 1
    assert out["variables"] == ["a", "b", "c"]
```

## Available parsers

- [JSON Parser](parsers/json_parser.md): extracts structured fields from JSON-formatted logs.
- [Template Matcher](parsers/template_matcher.md): matches logs against a predefined set of `<*>` templates.
- [Template Tree Matcher](parsers/template_tree_matcher.md): matches logs against a predefined set of `<*>` templates using a tree structure.
- [LogBatcher Parser](parsers/logbatcher_parser.md): LLM-based parser that infers templates from raw logs with no training data.
- [Drain parser](parsers/drain_parser.md): Parser inspired by [Drain Publication](https://ieeexplore.ieee.org/document/8029742).
- [Brain Parser](parsers/brain.md) groups logs by token frequency to learn templates.
- [AECID-PG Parser](parsers/aecid_pg.md) learns templates by pruning a tree of token sequences.
- [Auto parser](parsers/auto_parser.md): The auto parser uses a brute-force strategy: it iterates through every log-type record in the internal dataset and chooses the regex and templates that best matches the provided logs.

### Common parameters (all parsers)

All parsers inherit parameters from `CoreParserConfig`, `CoreConfig`, and `BasicConfig`. Each parser’s page explains its specific parameters.

<!-- Start common_arguments -->
???+ note "Top level"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `auto_config` | boolean | False | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `start_id` | integer | 10 | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | Reuse configuration records as training data. |
    | `train_buffer_max_records` | integer | 100000 | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | Add a connector to the output schema. |
    | `connector_url` | string, null | None | Set up the URL of the connector for the output schema. |
    | `log_format` | string, null | None | Pattern with named fields such as `<Time>` and `<Content>` for splitting a raw log. |
    | `time_format` | string, null | None | Format used to parse the timestamp field. |
    | `log_source` | string, null | None | Process only inputs of the same log source. |
<!-- End common_arguments -->

### Parser generators

Drain, Brain, and AECID-PG use `ParserGenerator` to learn templates from buffered logs and merge templates during [federation](federation.md). Their configs inherit these additional fields from `ParserGeneratorConfig`. Each parser defines its own default `Finetune` search grid. The search runs when `auto_config` is enabled and `data_use_configure` is set.

<!-- Start parser_generator_arguments -->
???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `reset_in_post_train` | boolean | False | Clear buffered training logs after generating templates. |
    | `Finetune` | array | [] | Candidate [parameter, values] pairs for automatic configuration. |
<!-- End parser_generator_arguments -->
