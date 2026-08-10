# New Value Detector

The New Value Detector raises alerts when previously unseen values appear in configured fields (for example new user names, IP addresses, or process names). It is useful to detect novelty, configuration drift, or the appearance of new actors in the environment.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

This detector maintains a lightweight set of observed values per monitored field and emits an alert when a value not present in the set is seen for the first time (subject to configuration).


## Configuration example

```yaml
detectors:
    NewValueDetector:
        method_type: new_value_detector
        auto_config: False
        params: {}
        persist:                      # optional — omit to disable saving
          path: ./state
          interval_seconds: 300
          auto_load: false
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
--8<-- "docs/examples/detectors/new_value.py:example"
```

Go back [Index](../index.md)
