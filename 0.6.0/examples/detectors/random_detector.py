# --8<-- [start:example]
import numpy as np
import yaml
from detectmatelibrary import schemas
from detectmatelibrary.detectors.random_detector import RandomDetector

with open("docs/examples/detectors/random_detector.yaml") as f:
    config = yaml.safe_load(f)
detector = RandomDetector(name="RandomDetector", config=config)

login = schemas.ParserSchema({"EventID": 0, "variables": ["alice", "10.0.0.1", "22"]})

np.random.seed(0)  # only to make this example reproducible

# no training needed: with threshold 0.9, roughly 1 in 10 logs raises an alert
alerts = [detector.process(login) for _ in range(100)]
print(sum(alert is not None for alert in alerts))  # around 10
# --8<-- [end:example]
