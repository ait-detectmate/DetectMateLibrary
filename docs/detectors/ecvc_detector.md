# ECVC Detector

The Event Count Vector Clustering Detector (ECVC) detect anomalies by calculating the distance between the count vectors from training and new ones. The method can be found in [this publication](https://dl.acm.org/doi/10.1145/3660768).

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

A count vector is form by counting the number of appearance of each event ID in a sequence of a specific window size.


## Configuration example

```yaml
detectors:
    SCVSDetector:
        method_type: scvs_detector
        window_size: 10
```


## Example usage

```python
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "ECVCDetector": {
            "method_type": "ecvc_detector_detector",
            "window_size": 10,
            "validation_per": 0.2,
            "threshold_method": "mean"  # mean, default (default = threshold 0)
        }
    }
}
detector = ECVCDetector(name="ECVCDetector", config=cfg)

parser_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["var1"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})


alert = detector.process(parser_data)
```

Go back [Index](../index.md)
