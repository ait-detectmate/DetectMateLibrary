# JSON Parser

Extracts structured information from JSON-formatted logs. Optionally delegates parsing of a specific JSON field (the "content") to another parser (for example, the Template matcher).

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Raw log (JSON string) |
| **Output** | [ParserSchema](../schemas.md) | Structured log with extracted fields |

## Configuration

Relevant config options (example names used by the implementation):

- `method_type` (string): parser type identifier (`json_parser`).
- `params.timestamp_name` (string): JSON key to use as the timestamp (default `"time"`).
- `params.content_name` (string): JSON key whose value is parsed further (default `"message"`).
- `params.content_parser` (string): name of a **sibling top-level parser entry**
  used to parse the extracted content (default `"JsonMatcherParser"`).

Example YAML fragment:

```yaml
parsers:
  JsonParser:
    method_type: json_parser
    params:
      timestamp_name: "time"
      content_name: "message"
      content_parser: JsonMatcherParser
  JsonMatcherParser:
    method_type: matcher_parser
    params:
      path_templates: tests/test_folder/test_templates.txt
```


## Usage examples

Basic usage — parse JSON and extract fields:

```python
import json
from detectmatelibrary.parsers.json_parser import JsonParser, JsonParserConfig
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
print(output.logFormatVariables["request.path"])  # "/api/users"
```

Go back [Index](../index.md)
