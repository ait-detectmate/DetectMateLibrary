# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector

with open("docs/examples/detectors/ecvc_detector.yaml") as f:
    config = yaml.safe_load(f)
detector = ECVCDetector(name="ECVCDetector", config=config)


def event(event_id: int) -> schemas.ParserSchema:
    """A parsed log; only its EventID (the matched template) matters here."""
    return schemas.ParserSchema({"EventID": event_id})


# normal session: 0 = login accepted, 1 = session opened, 2 = session closed.
# The detector works on sliding windows of 3 logs (window_size: 3).
for log in [event(i) for i in [0, 1, 2] * 8]:
    detector.process(log)

# a burst of logins: windows whose EventID counts are far from anything learned
alerts = [detector.process(event(0)) for _ in range(4)]
print([alert["score"] if alert else None for alert in alerts])  # [None, 0.5, 0.8, 0.8]
# --8<-- [end:example]
