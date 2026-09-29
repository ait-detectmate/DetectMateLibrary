# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.logbert_detector import LogBertDetector

with open("docs/examples/detectors/logbert_detector.yaml") as f:
    config = yaml.safe_load(f)
detector = LogBertDetector(name="LogBertDetector", config=config)


def event(event_id: int) -> schemas.ParserSchema:
    """A parsed log; only its EventID (the matched template) matters here."""
    return schemas.ParserSchema({"EventID": event_id})


# a repeating workflow of 4 events; the model trains once 60 windows are collected
for log in [event(i) for i in [0, 1, 2, 3] * 15]:
    detector.process(log)

# the same workflow, but with events 2 and 3 swapped in the middle
stream = [0, 1, 2, 3, 0, 1, 3, 2, 0, 1, 2, 3]
flagged = [i for i, e in enumerate(stream) if detector.process(event(e))]
# Positions of the flagged windows. On a stream this small LogBERT also flags
# some normal windows; in practice, train it on thousands of logs.
print(flagged)
# --8<-- [end:example]
