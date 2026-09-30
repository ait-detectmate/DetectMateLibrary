# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.charset_detector import CharsetDetector

with open("docs/examples/detectors/charset.yaml") as f:
    config = yaml.safe_load(f)
detector = CharsetDetector(name="UserCharsetDetector", config=config)


def failed_login(user: str) -> schemas.ParserSchema:
    """What a parser emits for 'Failed password for <user> from 10.0.0.1 port
    22'."""
    return schemas.ParserSchema({"EventID": 1, "variables": [user, "10.0.0.1", "22"]})


# the first 3 logs train the detector (data_use_training: 3)
for log in [failed_login("alice"), failed_login("bob"), failed_login("carol")]:
    detector.process(log)

print(detector.process(failed_login("carla")))  # None: only known characters
alert = detector.process(failed_login("bob;rm -rf"))
print(dict(alert["alertsObtain"]))
# {'EventID 1 - user': "Unknown character(s): ' ', '-', ';', 'f', 'm'"}
# --8<-- [end:example]
