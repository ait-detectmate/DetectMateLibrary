# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.new_event_detector import NewEventDetector

with open("docs/examples/detectors/new_event.yaml") as f:
    config = yaml.safe_load(f)
detector = NewEventDetector(name="NewEventDetector", config=config)


def event(event_id: int) -> schemas.ParserSchema:
    """A parsed log; only its EventID (the matched template) matters here."""
    return schemas.ParserSchema({"EventID": event_id})


# the first 3 logs train the detector (data_use_training: 3):
# EventID 0 = "Accepted password ...", EventID 1 = "Failed password ..."
for log in [event(0), event(1), event(0)]:
    detector.process(log)

print(detector.process(event(1)))  # None: known event
alert = detector.process(event(2))  # a template never seen during training
print(dict(alert["alertsObtain"]))  # {'EventID 2 - {}': "Unknown event ID: '2'"}
# --8<-- [end:example]
