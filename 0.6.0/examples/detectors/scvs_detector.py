# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.scvs_detector import SCVSDetector

with open("docs/examples/detectors/scvs_detector.yaml") as f:
    config = yaml.safe_load(f)
detector = SCVSDetector(name="SCVSDetector", config=config)


def event(event_id: int) -> schemas.ParserSchema:
    """A parsed log; only its EventID (the matched template) matters here."""
    return schemas.ParserSchema({"EventID": event_id})


# normal session: 0 = login accepted, 1 = session opened, 2 = session closed.
# The detector works on sliding windows of 3 logs (window_size: 3).
for log in [event(i) for i in [0, 1, 2] * 3]:
    detector.process(log)

# three logins in a row: a window whose EventID counts were never seen
alerts = [detector.process(event(0)) for _ in range(3)]
print([alert["score"] if alert else None for alert in alerts])  # [None, 1.0, 1.0]
# --8<-- [end:example]
