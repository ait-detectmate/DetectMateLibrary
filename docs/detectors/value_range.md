# Value Range Detector

The Value Range Detector raises alerts when numerical values outside of known ranges appear in configured fields. It is useful to detect unexpected changes, configuration drift, or the appearance of new actors in the environment.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

This detector maintains a lightweight set of observed values per monitored field and emits an alert when a value outside the learned range is seen (subject to configuration).


## Configuration example

```yaml
detectors:
    ValueRangeDetector:
        method_type: value_range_detector
        auto_config: False
        params: {"ignore_non_numerical_val": True}
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
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetector, BufferMode
import detectmatelibrary.schemas as schemas

detector = ValueRangeDetector(name="NewValueTest", config=cfg)

parser_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["1", "2", "17"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})


alert = detector.process(parsed_data)
```

Go back [Index](../index.md)
