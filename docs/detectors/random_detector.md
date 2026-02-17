# Random Detector

It return random alerts when receiving parserd logs.

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md)| Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alerts produced |


## Configuration file

Example of a configuration file:

```yaml
    RandomDetector:
        method_type: random_detector
        auto_config: False
        params: {}
        events:
            1:
                test:
                    params: {}
                    variables:
                        - pos: 0
                          name: var1
                          params:
                              threshold: 0.
                    header_variables:
                        - pos: level
                          params: {}
```

## Example

Code examples of normal use cases of the detector:

```python
from detectmatelibrary.detectors.random_detector import RandomDetector

import detectmatelibrary.schemas as schemas


detector = RandomDetector(name="TestDetector", config=config)
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

detector.process(parser_data)
```

Go back [Index](../index.md)
