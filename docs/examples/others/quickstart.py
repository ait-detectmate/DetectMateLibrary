# --8<-- [start:parse]
from pathlib import Path
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From, To

ROOT = Path.cwd().resolve().parents[0]  # adjust if needed
templates_path = str(ROOT / "tests" / "test_data" / "audit_templates.txt")
log_path = str(ROOT / "tests" / "test_data" / "audit.log")
log_json = str(ROOT / "local" / "audit_raw.json")
parsed_path = str(ROOT / "local" / "audit_parsed.json")

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

# Collect first, write once: To.json re-reads and rewrites the whole output file
# on every call, so calling it inside the loop is O(n^2) and gets unusably slow
# (and fragile) on a real log file.
raw_logs = list(From.log(parser, log_path, do_process=False))
parsed_logs = [parser.process(log) for log in raw_logs]

To.json(raw_logs, log_json)
To.json(parsed_logs, parsed_path)
# --8<-- [end:parse]
