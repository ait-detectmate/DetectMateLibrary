# --8<-- [start:basic]
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
# --8<-- [end:basic]

# --8<-- [start:dict-based]
import json  # noqa: E402
from detectmatelibrary.parsers.json_parser import JsonParser  # noqa: E402
import detectmatelibrary.schemas as schemas  # noqa: E402
from pathlib import Path  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
templates = ROOT / "tests" / "test_data" / "test_templates.txt"

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
                "path_templates": str(templates)
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
# --8<-- [end:dict-based]
