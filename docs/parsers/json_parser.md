# JSON Parser

Extracts structured information from JSON-formatted logs. Optionally delegates parsing of a specific JSON field (the "content") to another parser (for example, the Template matcher).

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Raw log (JSON string) |
| **Output** | [ParserSchema](../schemas.md) | Structured log with extracted fields |

## Configuration

Relevant config options (example names used by the implementation):

- `method_type` (string): parser type identifier (e.g. `json_parser`).
- `params.timestamp_name` (string | null): JSON key to use as the received/parsed timestamp.
- `params.content_name` (string): JSON key that contains the textual content to parse further (default `"message"` or `"content"`).
- `params.flatten_nested` (bool, default True): flatten nested objects into dot-separated keys in `logFormatVariables`.
- `params.content_parser` (string | dict): optional parser spec (name or config) to parse the extracted content.
- `params.ignore_parse_errors` (bool, default True): if True, parser returns gracefully on JSON errors instead of raising.

Example YAML fragment:

```yaml
parsers:
  JsonParser:
    method_type: json_parser
    params:
      timestamp_name: "time"
      content_name: "message"
      flatten_nested: True
      content_parser:
        method_type: matcher_parser
        params:
          path_templates: tests/test_templates.txt
      ignore_parse_errors: True
```


## Usage examples

Basic usage — parse JSON and extract fields:

```python
from detectmatelibrary.parsers.json_parser import JsonParser

import detectmatelibrary.schemas as schemas


config = JsonParserConfig()
parser = JsonParser(name="TestParser", config=config)

json_log = {
    "time": "2023-11-18 10:30:00",
    "request": {
        "method": "GET",
        "path": "/api/users",
        "headers": {
            "content-type": "application/json"
        }
    }
}

input_log = schemas.LogSchema({
    "logID": "1",
    "log": json.dumps(json_log)
})

output = schemas.ParserSchema()
parser.parse(input_log, output)

print(output.logFormatVariables["request.method"])  # "GET"
print(output.logFormatVariables["request.path"])  #"/api/users"
```

Go back [Index](../index.md)
