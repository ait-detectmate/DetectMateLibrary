# --8<-- [start:basic]
import json
from detectmatelibrary.parsers.json_parser import JsonParser
from detectmatelibrary import schemas

parser = JsonParser(name="JsonParser")  # all defaults: flattens the JSON fields

json_log = {
    "time": "2023-11-18 10:30:00",
    "request": {"method": "GET", "path": "/api/users"},
}
output = schemas.ParserSchema()
parser.parse(schemas.LogSchema({"logID": "1", "log": json.dumps(json_log)}), output)

print(output.logFormatVariables["request.method"])  # GET
print(output.logFormatVariables["request.path"])    # /api/users
# --8<-- [end:basic]

# --8<-- [start:dict-based]
import yaml  # noqa: E402

with open("docs/examples/parsers/json_parser.yaml") as f:
    config = yaml.safe_load(f)
parser = JsonParser(name="JsonParser", config=config)

json_log = {
    "time": "2023-11-18 10:30:00",
    "message": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"",
    "level": "INFO",
}
output = schemas.ParserSchema()
parser.parse(schemas.LogSchema({"logID": "1", "log": json.dumps(json_log)}), output)

print(output.logFormatVariables["level"])  # INFO
print(output.template)                     # pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>
# --8<-- [end:dict-based]
