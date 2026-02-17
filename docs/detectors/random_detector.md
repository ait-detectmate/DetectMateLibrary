# Random Detector

The Random Detector produces randomized alerts for incoming parsed logs. It is useful for testing pipelines, alert routing, and downstream consumers without needing a real detection model.

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Generated alerts |

## Description

The detector inspects incoming ParserSchema instances and, according to its configuration, emits alerts with synthetic content. It can be configured to sample specific log variables, set thresholds or control alert frequency. Use it for integration testing, load testing, or as a simple example of a detector implementation.

## Configuration example

```yaml
detectors:
  RandomDetector:
    method_type: random_detector
    auto_config: False
    params:
      log_variables:
        - id: test
          event: 1
          template: dummy_template
          variables:
            - pos: 0
              name: var1
              params:
                threshold: 0.0
          header_variables:
            - pos: level
              params: {}
```

## Example usage

```python
from detectmatelibrary.detectors.random_detector import RandomDetector
import detectmatelibrary.schemas as schemas

# assume `config` is loaded from YAML and converted to the detector Config class
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

# process returns True if an alert was emitted, False otherwise
alert_emitted = detector.process(parser_data)
```

Go back [Index](../index.md)
