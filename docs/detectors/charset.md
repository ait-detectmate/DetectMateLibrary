# Charset Detector

The Charset Detector raises alerts when previously unseen characters appear in configured fields. It is useful to detect novelty, configuration drift, or the appearance of new actors in the environment.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

This detector maintains a lightweight set of observed characters per monitored field and emits an alert when a character not present in the set is seen for the first time (subject to configuration).


## Configuration example

```yaml
detectors:
    CharsetDetector:
        method_type: charset_detector
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
--8<-- "docs/examples/detectors/charset.py:example"
```

Go back [Index](../index.md)
