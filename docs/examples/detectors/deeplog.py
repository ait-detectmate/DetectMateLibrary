# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetector

with open("docs/examples/detectors/deeplog.yaml") as f:
    config = yaml.safe_load(f)
detector = DeeplogDetector(name="DeeplogDetector", config=config)


def event(event_id: int) -> schemas.ParserSchema:
    """A parsed log; only its EventID (the matched template) matters here."""
    return schemas.ParserSchema({"EventID": event_id})


# a repeating workflow of 4 events; the model trains once 60 windows are collected
for log in [event(i) for i in [0, 1, 2, 3] * 15]:
    detector.process(log)

# the same workflow, but with events 2 and 3 swapped in the middle
stream = [0, 1, 2, 3, 0, 1, 3, 2, 0, 1, 2, 3]
flagged = [i for i, e in enumerate(stream) if detector.process(event(e))]
print(flagged)  # [6, 7]: the windows ending on the swapped events
# --8<-- [end:example]
