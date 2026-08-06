# SCVS Detector

The Sequence Count Vector Set Detector (SCVS) detects anomalies by finding count vectors that were not present in the training dataset.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

A count vector is formed by counting the number of appearance of each event ID in a sequence of a specific window size.


## Configuration example

```yaml
detectors:
    SCVSDetector:
        method_type: scvs_detector
        window_size: 10
```


## Example usage

```python
from detectmatelibrary.detectors.scvs_detector import SCVSDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "SCVSDetector": {
            "method_type": "scvs_detector",
            "auto_config": False,
        }
    }
}
detector = SCVSDetector(name="NewValueTest", config=cfg)

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
