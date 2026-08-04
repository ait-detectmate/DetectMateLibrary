# --8<-- [start:example]
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary import schemas
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
templates = ROOT / "tests" / "test_data" / "test_templates.txt"
# instantiate parser (config can be a dict or config object)
cfg = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "params": {
                "path_templates": str(templates),
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True
            }
        }
    }
}

parser = MatcherParser(name="MatcherParser", config=cfg)

# match a log
input_log = schemas.LogSchema({"logID": "0", "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'"})
parsed = parser.process(input_log)  # or parser.parse / parser.match depending on wrapper API

# parsed is a ParserSchema (or an output container). Check fields:
print(parsed.template)         # matched template text
print(parsed.variables)        # list of extracted params
# --8<-- [end:example]