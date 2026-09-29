# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetector

with open("docs/examples/detectors/event_sequence.yaml") as f:
    config = yaml.safe_load(f)
detector = EventSequenceDetector(name="LoginSequenceDetector", config=config)


def event(event_id: int) -> schemas.ParserSchema:
    """A parsed log; only its EventID (the matched template) matters here."""
    return schemas.ParserSchema({"EventID": event_id})


# normal session: 0 = login accepted, 1 = session opened, 2 = session closed.
# The first 6 logs train the detector (data_use_training: 6).
for log in [event(i) for i in [0, 1, 2, 0, 1, 2]]:
    detector.process(log)

for i in [0, 1, 2]:
    print(detector.process(event(i)))  # None: every pair was seen in training

detector.process(event(0))
alert = detector.process(event(2))  # session closed without being opened
print(dict(alert["alertsObtain"]))
# {'Sequence (0, 2)': 'EventID sequence of length 2 ending at logID  was not seen during training.'}

print(detector.get_known_sequences())  # {(0, 1), (1, 2), (2, 0)}
# --8<-- [end:example]
