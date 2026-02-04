# Json Parser

Extracts the log from a json format. It can use a second parser to parse the log information.

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md)| Unstructured log   |
| **Output** | [ParserSchema](../schemas.md)| Structured log  |


## Configuration file

Example of a configuration file:

```yaml
parsers:
    JsonMatcherParser:
        method_type: matcher_parser
        auto_config: False
        log_format: "<Content>"
        time_format: null
        params:
            remove_spaces: True
            remove_punctuation: True
            lowercase: True
            path_templates: local/miranda_templates.txt

    JsonParser:
        method_type: json_parser
        time_format: null
        auto_config: False
        params:
            timestamp_name: "time"
            content_name: "message"
            content_parser: JsonMatcherParser
```

## Example

Code examples of normal use cases of the parser:

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
