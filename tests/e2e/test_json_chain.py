"""Chain C8: JSON log lines -> JsonParser (a MatcherParser for the message)
-> NewValueDetector.

audit.log is rewritten as one JSON object per line ({"time", "Type",
"message"}). The content parser gets NewValue's chain C3 parser settings, and
the detector its C3 config, so the alerts must be the ones in NewValue's C3
golden file: the header fields that log_format extracted come from the JSON
keys here.
"""
import json
import re
from pathlib import Path

from detectmatelibrary.detectors import NewValueDetector
from detectmatelibrary.helper.from_to import From
from detectmatelibrary.parsers import JsonParser
from tests.support import golden as golden_files
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

AUDIT_LINE = re.compile(r"type=(?P<Type>\S+) msg=audit\((?P<time>[^)]+)\): (?P<message>.*)")


def _write_json_lines(path: str) -> None:
    with open(AUDIT_LOG) as f:
        lines = [json.dumps(AUDIT_LINE.fullmatch(line.rstrip("\n")).groupdict()) for line in f]
    Path(path).write_text("\n".join(lines) + "\n")


def test_json_logs_raise_the_golden_alerts():
    golden = golden_files.read("audit/NewValueDetector")
    content_parser = {"method_type": "matcher_parser", "auto_config": False,
                      "params": {**golden["parser"]["params"], "path_templates": AUDIT_TEMPLATES}}
    parser = JsonParser(config={"parsers": {
        "JsonParser": {"method_type": "json_parser", "auto_config": False, "params": {}},
        "JsonMatcherParser": content_parser,
    }})
    detector = NewValueDetector(config={"detectors": {"NewValueDetector": golden["config"]}})
    _write_json_lines("audit.jsonl")

    parsed = list(From.log(parser, "audit.jsonl", do_process=True))
    alerts = [list(output["logIDs"]) for output in map(detector.process, parsed) if output is not None]

    assert parsed[0]["headerVariables"]["Type"] == "USER_ACCT"
    assert alerts == golden["alerts"]
