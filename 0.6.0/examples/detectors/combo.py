# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector

with open("docs/examples/detectors/combo.yaml") as f:
    config = yaml.safe_load(f)
detector = NewValueComboDetector(name="UserIpComboDetector", config=config)


def login(user: str, ip: str) -> schemas.ParserSchema:
    """What a parser emits for 'Accepted password for <user> from <ip> port
    22'."""
    return schemas.ParserSchema({"EventID": 0, "variables": [user, ip, "22"]})


# the first 3 logs train the detector (data_use_training: 3)
for log in [login("alice", "10.0.0.1"), login("bob", "10.0.0.2"), login("alice", "10.0.0.1")]:
    detector.process(log)

print(detector.process(login("bob", "10.0.0.2")))  # None: known user/IP pair
# alice and 10.0.0.2 are both known, but never appeared together
alert = detector.process(login("alice", "10.0.0.2"))
print(dict(alert["alertsObtain"]))
# {"EventID 0 - ('user', 'src_ip')": "Unknown value combination: ('alice', '10.0.0.2')"}
# --8<-- [end:example]
