# New Value Detector

The New Value Detector raises alerts when previously unseen values appear in configured fields (for example new user names, IP addresses, or process names). It is useful to detect novelty, configuration drift, or the appearance of new actors in the environment.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

This detector maintains a lightweight set of observed values per monitored field and emits an alert when a value not present in the set is seen for the first time (subject to configuration). .


## Configuration example

```yaml
detectors:
    NewValueDetector:
        method_type: new_value_detector
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


## Example usage

```python
from detectmatelibrary.detectors.new_value_detector import NewValueDetector, BufferMode
import detectmatelibrary.schemas as schemas

detector = NewValueDetector(name="NewValueTest", config=cfg)

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


alert = detector.process(parsed_data)
```

Go back [Index](../index.md)
