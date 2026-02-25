# Components: Parsers

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

## CoreParser — minimal API

Recommended signatures and behavior:

```python
class CoreParser:
    def run(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        """Top-level runner. Calls parse() and performs pre/post processing.
        Return True when a parsed output was produced, False otherwise.
        """

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        """Implement parsing here.
        - Fill required output_ fields (see ParserSchema table below).
        - Return True if parsing succeeded and output_ contains a result.
        """

    def train(self, input_: Iterable[schemas.LogSchema]) -> None:
        """Optional: train internal models. Can be a no-op for stateless parsers."""
```

## ParserSchema — what to populate

Minimum fields commonly expected by downstream components:

- `EventID` (int) — identifier for the matched template/event
- `template` (string) — event template text
- `variables` (repeated string) — extracted parameters (extend the list)
- `parsedLogID` / `logID` — identifiers linking raw and parsed records
- `parsedTimestamp` / `receivedTimestamp` — timestamps


## Creating a new parser — step by step

1. Create a Config class inheriting `CoreParserConfig`.
2. Create parser class inheriting `CoreParser`.
3. Implement `parse()` to populate `output_`.
4. Add unit tests for `parse()` behavior.

Example:

```python
# filepath: src/detectmatelibrary/parsers/my_parser.py
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas
from typing import Any

class MyParserConfig(CoreParserConfig):
    method_type: str = "my_parser"
    # add parser-specific settings here
    pattern: str | None = None

class MyParser(CoreParser):
    def __init__(self, name: str = "MyParser", config: MyParserConfig | dict[str, Any] = MyParserConfig()):
        if isinstance(config, dict):
            config = MyParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

    def parse(self, input_: schemas.LogSchema, output_: schemas.ParserSchema) -> bool:
        text = input_.log or ""
        # simple example: split on whitespace and treat as variables
        tokens = text.split()
        output_["EventID"] = 1
        output_["template"] = " ".join(["<*>"] * len(tokens))
        output_["variables"].extend(tokens)
        output_["parsedTimestamp"] = int(time.time())
        return True
```

## Testing parsers

Unit test `parse()` directly using `ParserSchema` objects:

```python
def test_my_parser_parse():
    from detectmatelibrary.parsers.my_parser import MyParser
    from detectmatelibrary import schemas

    parser = MyParser()
    raw = schemas.LogSchema({"log": "a b c", "logID": "1"})
    out = schemas.ParserSchema()
    ok = parser.parse(raw, out)
    assert ok is True
    assert out["EventID"] == 1
    assert out["variables"] == ["a", "b", "c"]
```

Go back to [Index](index.md)
