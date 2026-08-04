# --8<-- [start:example]
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcher
from detectmatelibrary import schemas
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
templates = ROOT / "tests" / "test_data" / "test_templates.txt"
# instantiate parser (config can be a dict or a config object)
cfg = {
    "parsers": {
        "TreeMatcher": {
            "method_type": "tree_matcher",
            "params": {
                "path_templates": str(templates)
            }
        }
    }
}

parser = TemplateCppTreeMatcher(name="TreeMatcher", config=cfg)

# match a log
input_log = schemas.LogSchema({
    "logID": "0",
    "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'"
})
parsed = parser.process(input_log)  # or call parser.parse / parser.match depending on the API

# parsed is a ParserSchema. Inspect fields:
print(parsed.template)   # matched template text
print(parsed.variables)  # list of extracted parameters
# --8<-- [end:example]