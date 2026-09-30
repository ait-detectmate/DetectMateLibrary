# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.rule_detector import RuleDetector

with open("docs/examples/detectors/rule_based.yaml") as f:
    config = yaml.safe_load(f)
detector = RuleDetector(name="RuleDetector", config=config)


def parsed(event_id: int, log: str, level: str = "INFO") -> schemas.ParserSchema:
    """A parsed log; EventID -1 means the parser found no matching template."""
    return schemas.ParserSchema({"EventID": event_id, "log": log, "logFormatVariables": {"Level": level}})


logs = [
    parsed(0, "Accepted password for alice from 10.0.0.1 port 22"),
    parsed(-1, "kernel: unexpected garbled line"),
    parsed(3, "alice : TTY=pts/0 ; COMMAND=/usr/bin/sudo su"),
    parsed(1, "Failed password for root from 10.0.0.9 port 22", level="ERROR"),
]
for log in logs:
    alert = detector.process(log)
    print(dict(alert["alertsObtain"]) if alert else None)
# None
# {'R001 - TemplateNotFound': 'No template found by parser'}
# {'R002 - SpecificKeyword': "Found word 'sudo' in the logs"}
# {'R004 - ErrorLevelFound': 'Error found'}
# --8<-- [end:example]
