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
      path_templates: src/detectmatelibrary/testutils/data/test_templates.txt
```


## Usage examples

Basic usage — parse JSON and extract fields (no template matching):

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

print(output.logFormatVariables["request.method"])   # "GET"
print(output.logFormatVariables["request.path"])     # "/api/users"
```

Dict-based config (from YAML) — with template matching on the `message` field:

```python
import json
from detectmatelibrary.parsers.json_parser import JsonParser
import detectmatelibrary.schemas as schemas


config_dict = {
    "parsers": {
        "JsonParser": {
            "method_type": "json_parser",
            "params": {
                "timestamp_name": "time",
                "content_name": "message",
            }
        },
        "JsonMatcherParser": {
            "method_type": "matcher_parser",
            "params": {
                "path_templates": "tests/test_templates.txt"
            }
        }
    }
}
parser = JsonParser(name="JsonParser", config=config_dict)

json_log = {
    "time": "2023-11-18 10:30:00",
    "message": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"",
    "level": "INFO"
}

input_log = schemas.LogSchema({
    "logID": "1",
    "log": json.dumps(json_log)
})

output = schemas.ParserSchema()
parser.parse(input_log, output)

print(output.logFormatVariables["level"])  # "INFO"
print(output.template)                     # "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>"
```

Go back [Index](../index.md)
