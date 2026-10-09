# --8<-- [start:example]
from detectmatelibrary import schemas
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.detectors.new_value_detector import NewValueDetector

# Templates from a CSV file: the EventId column names each template, and
# named wildcards (<user>, <ip>, <port>) name its variables.
parser = MatcherParser(name="MatcherParser", config={"parsers": {"MatcherParser": {
    "method_type": "matcher_parser",
    "path_templates": "docs/examples/data/named_templates.csv",
}}})

# The detector configuration uses those names instead of numbers.
detector = NewValueDetector(name="NewUserDetector", config={"detectors": {"NewUserDetector": {
    "method_type": "new_value_detector",
    "auto_config": False,
    "params": {"data_use_training": 2},
    "events": {
        "login_failure": {                                  # EventId from the CSV
            "failed_login": {
                "variables": [{"pos": "user", "name": "user"}],  # named wildcard <user>
            },
        },
    },
}}})

# Resolve the names to the numbers the parser emits (login_failure -> 1, user -> 0).
# Without this step the detector monitors nothing.
detector.config.events = parser.template_matcher.compile_detector_config(detector.config.events)

lines = [
    "Failed password for alice from 10.0.0.1 port 22",    # training
    "Failed password for alice from 10.0.0.2 port 22",    # training
    "Failed password for mallory from 10.0.0.3 port 22",  # new user
]
for line in lines:
    alert = detector.process(parser.process(schemas.LogSchema({"log": line})))
    print(dict(alert["alertsObtain"]) if alert else None)
# None
# None
# {'EventID 1 - user': "Unknown value: 'mallory'"}
# --8<-- [end:example]
