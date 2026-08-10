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

## Example usage

```python
--8<-- "docs/examples/detectors/random_detector.py:example"
```

Go back [Index](../index.md)
