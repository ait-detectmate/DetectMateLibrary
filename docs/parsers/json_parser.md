# JSON Parser

Extracts structured information from JSON-formatted logs. Optionally delegates parsing of a specific JSON field (the "content") to a sibling Template Matcher parser. Nested JSON objects are always flattened to dot-separated keys in `logFormatVariables`.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Raw log (JSON string) |
| **Output** | [ParserSchema](../schemas.md) | Structured log with extracted fields |

## Configuration

Relevant config options:

- `method_type` (string): parser type identifier — must be `json_parser`.
- `params.timestamp_name` (string): JSON key to use as the timestamp (default `"time"`).
- `params.content_name` (string): JSON key whose value is forwarded to the content parser (default `"message"`).
- `params.content_parser` (string): name of a **sibling** parser entry in the `parsers` section that handles the content field (default `"JsonMatcherParser"`).

The `content_parser` value is a **name**, not an inline config. The referenced parser must be defined as a separate sibling entry at the same level as `JsonParser`.

Example YAML fragment:

```yaml
parsers:
  JsonParser:
    method_type: json_parser
    params:
      timestamp_name: "time"
      content_name: "message"
      content_parser: JsonMatcherParser   # optional — defaults to "JsonMatcherParser"
  JsonMatcherParser:
    method_type: matcher_parser
    params:
      path_templates: tests/test_data/test_templates.txt
```


## Usage examples

Basic usage — parse JSON and extract fields (no template matching):

```python
--8<-- "docs/examples/parsers/json_parser.py:basic"
```

Dict-based config (from YAML) — with template matching on the `message` field:

```python
--8<-- "docs/examples/parsers/json_parser.py:dict-based"
```

Go back [Index](../index.md)
