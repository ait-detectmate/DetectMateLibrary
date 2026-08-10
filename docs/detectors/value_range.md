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
--8<-- "docs/examples/detectors/value_range.py:example"
```

Go back [Index](../index.md)
