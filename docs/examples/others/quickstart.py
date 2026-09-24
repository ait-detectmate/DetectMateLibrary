# --8<-- [start:parse]
from pathlib import Path
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From, To

ROOT = Path(__file__).resolve().parents[3]  # repository root; adjust if needed
templates_path = str(ROOT / "tests" / "test_data" / "audit_templates.txt")
log_path = str(ROOT / "tests" / "test_data" / "audit.log")
log_json = str(ROOT / "local" / "audit_raw.json")
parsed_path = str(ROOT / "local" / "audit_parsed.json")
(ROOT / "local").mkdir(exist_ok=True)

config_dict = {
    "parsers": {
        "MatcherParser": {
            "auto_config": True,
            "method_type": "matcher_parser",
            "path_templates": templates_path,
            "log_format": r"type=<Type> msg=audit\(<Time>:<Serial>\): <Content>",
        }
    }
}
parser = MatcherParser(name="MatcherParser", config=config_dict)

raw_logs = list(From.log(parser, log_path, do_process=False))
parsed_logs = [parser.process(log) for log in raw_logs]

To.json(raw_logs, log_json)
To.json(parsed_logs, parsed_path)
# --8<-- [end:parse]
