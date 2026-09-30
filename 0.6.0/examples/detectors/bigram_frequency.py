# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.bigram_frequency_detector import BigramFrequencyDetector

with open("docs/examples/detectors/bigram_frequency.yaml") as f:
    config = yaml.safe_load(f)
detector = BigramFrequencyDetector(name="UserBigramDetector", config=config)


def failed_login(user: str) -> schemas.ParserSchema:
    """What a parser emits for 'Failed password for <user> from 10.0.0.1 port
    22'."""
    return schemas.ParserSchema({"EventID": 1, "variables": [user, "10.0.0.1", "22"]})


# the first 4 logs train the detector (data_use_training: 4)
for log in [failed_login(u) for u in ["alice", "alicia", "alina", "alex"]]:
    detector.process(log)

print(detector.process(failed_login("alia")))  # None: familiar character pairs
alert = detector.process(failed_login("xq7zv9k"))  # random-looking user name
print(dict(alert["alertsObtain"]))
# {'EventID 1 - user': 'Bigram frequency anomaly with value xq7zv9k, critical_val 0.0 and threshold 0.05.'}
# --8<-- [end:example]
