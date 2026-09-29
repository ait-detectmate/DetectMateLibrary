# --8<-- [start:example]
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetector

with open("docs/examples/detectors/value_range.yaml") as f:
    config = yaml.safe_load(f)
detector = ValueRangeDetector(name="DownloadSizeDetector", config=config)


def download(path: str, bytes_read: int) -> schemas.ParserSchema:
    """What a parser emits for 'close <path> bytes read <bytes_read> written
    0'."""
    return schemas.ParserSchema({"EventID": 2, "variables": [path, str(bytes_read), "0"]})


# the first 3 logs train the detector (data_use_training: 3)
for log in [download("/srv/a.pdf", 100), download("/srv/b.pdf", 250), download("/srv/c.pdf", 180)]:
    detector.process(log)

print(detector.process(download("/srv/d.pdf", 200)))  # None: inside the learned range
alert = detector.process(download("/srv/db.dump", 99999))
print(dict(alert["alertsObtain"]))  # {'EventID 2 - bytes_read': "Out of range value: '99999' (100 - 250)"}
# --8<-- [end:example]
