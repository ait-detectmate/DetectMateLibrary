# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.new_value_detector import NewValueDetector

with open("docs/examples/detectors/new_value.yaml") as f:
    config = yaml.safe_load(f)
detector = NewValueDetector(name="NewUserDetector", config=config)


def login(user: str, ip: str) -> schemas.ParserSchema:
    """What a parser emits for 'Accepted password for <user> from <ip> port
    22'."""
    return schemas.ParserSchema({"EventID": 0, "variables": [user, ip, "22"]})


# the first 3 logs train the detector (data_use_training: 3)
for log in [login("alice", "10.0.0.1"), login("bob", "10.0.0.2"), login("alice", "10.0.0.3")]:
    detector.process(log)

print(detector.process(login("bob", "10.0.0.9")))  # None: bob is a known user
alert = detector.process(login("mallory", "10.0.0.1"))
print(dict(alert["alertsObtain"]))  # {'EventID 0 - user': "Unknown value: 'mallory'"}
# --8<-- [end:example]
