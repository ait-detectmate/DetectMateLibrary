# flake8: noqa
log_path = "tests/test_data/logs.log"
templates_path = "tests/test_data/audit_templates.txt"
parsed_path = "parsed_logs.json"
log_json = "logs.json"
alert_path = "alerts.json"


# --8<-- [start:example_1]
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From, To


config_dict = {
    "parsers": {
        "MatcherParser": {
            "auto_config": True,
            "method_type": "matcher_parser",
            "path_templates": templates_path,
            "log_format": r'type=<Type> msg=audit\(<Time>:<Serial>\): <Content>'
        }
    }
}
parser = MatcherParser(name="MatcherParser", config=config_dict)


for i, log in enumerate(From.log(parser, log_path, do_process=False)):
    To.json(log, log_json)

    parsed_log = parser.process(log)
    To.json(parsed_log, parsed_path)

# --8<-- [end:example_1]

# --8<-- [start:example_2]
from detectmatelibrary.detectors.random_detector import RandomDetector
from detectmatelibrary.helper.from_to import From, To, FromTo

config_dict = {
    "detectors": {
        "RandomDetector": {
            "auto_config": False,
            "method_type": "random_detector",
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 0,
                            "name": "process",
                            "params": {
                                "threshold": 0.
                            }
                        }]
                    }
                }
            }
        }
    }
}
detector =  RandomDetector(name="RandomDetector", config=config_dict)

for alert in FromTo.json2json(detector, parsed_path, alert_path):
    if alert is not None:
        print("Anomaly detected!")

# --8<-- [end:example_2]

import os

os.remove(parsed_path)
os.remove(log_json)
if os.path.exists(alert_path):
    os.remove(alert_path)
