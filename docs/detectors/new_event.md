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
--8<-- "docs/examples/detectors/new_event.py:example"
```

Go back [Index](../index.md)
