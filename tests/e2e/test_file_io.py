"""Chain C6: files in, files out. Raw audit.log lines -> FromTo.log2json
(parser) -> FromTo.json2yaml(detector) -> the alerts in a YAML file.

The detector (NewValue, set up as in its chain C3 golden file) first learns
the first TRAIN_UNTIL lines through process(). The file chain then runs on
a 40-line slice after them that holds every labelled anomaly: FromTo
rewrites its whole output file for every record, so all of audit.log would
take minutes (ISSUE_DRAFTS.md, Q-H). The YAML file must hold the slice's
golden alerts; From.log numbers the slice's lines from 0.
"""
from pathlib import Path

import yaml

from detectmatelibrary.detectors import NewValueDetector
from detectmatelibrary.helper.from_to import FromTo
from detectmatelibrary.parsers.template_matcher import MatcherParser
from tests.support import golden as golden_files
from tests.support.audit import TRAIN_UNTIL
from tests.support.paths import AUDIT_LOG, AUDIT_TEMPLATES

SLICE = range(1840, 1880)


def test_the_yaml_file_holds_the_golden_alerts(audit_logs):
    golden = golden_files.read("audit/NewValueDetector")
    detector = NewValueDetector(config={"detectors": {"NewValueDetector": golden["config"]}})
    for record in audit_logs(golden["parser"])[:TRAIN_UNTIL]:
        detector.process(record)
    entry = {"method_type": "matcher_parser", "auto_config": False, **golden["parser"]}
    entry["params"] = {**entry["params"], "path_templates": AUDIT_TEMPLATES}
    parser = MatcherParser(config={"parsers": {"MatcherParser": entry}})
    with open(AUDIT_LOG) as f:
        Path("slice.log").write_text("".join(f.readlines()[SLICE.start:SLICE.stop]))

    parsed = list(FromTo.log2json(parser, "slice.log", "parsed.json"))
    for _ in FromTo.json2yaml(detector, "parsed.json", "alerts.yaml"):
        pass

    assert len(parsed) == len(SLICE)
    with open("alerts.yaml") as f:
        written = yaml.safe_load(f)
    expected = [[str(int(log_id) - SLICE.start) for log_id in alert]
                for alert in golden["alerts"] if int(alert[-1]) in SLICE]
    assert [written[key]["logIDs"] for key in sorted(written)] == expected
