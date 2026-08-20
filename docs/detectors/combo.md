# Combo Detector

The New Combo Value Detector raises alerts when previously unseen combinations of values appear in configured fields (for example new user names, IP addresses, or process names). It is useful to detect novelty, configuration drift, or the appearance of new actors in the environment.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Combined alert / finding |

## Description
This detector maintains a lightweight set of observed combination of values per monitored fields and emits an alert when a combination is not present in the set seen for the first time (subject to configuration).

## Configuration

```yaml
detectors:
    NewValueComboDetector:
        method_type: new_value_combo_detector
        auto_config: False
        params:
            max_combo_size: 3
        events:
            1:
                test:
                    params: {}
                    variables:
                        - pos: 0
                          name: var1
                    header_variables:
                        - pos: level
```

## Example usage

```python
--8<-- "docs/examples/detectors/combo.py:example"
```

Go back [Index](../index.md)
