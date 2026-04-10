# New Event Detector

The New Event Detector raises alerts when previously unseen log templates, distinguished by event IDs, appear in log data. It is useful to detect unexpected types of events in the environment.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

This detector maintains a lightweight set of observed event IDs and emits an alert when an event ID not present in the set is seen for the first time (subject to configuration).


## Configuration example

```yaml
detectors:
    NewEventDetector:
        method_type: new_event_detector
        auto_config: False
        params: {}
```


## Example usage

```python
from detectmatelibrary.detectors.new_value_detector import NewValueDetector, BufferMode
import detectmatelibrary.schemas as schemas

detector = NewEventDetector(name="NewEventTest", config=cfg)

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
