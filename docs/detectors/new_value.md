# New Value Detector

The New Value Detector raises alerts when previously unseen values appear in configured fields (for example new user names, IP addresses, or process names). It is useful to detect novelty, configuration drift, or the appearance of new actors in the environment.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

✅ Federation compatible.


## Description

This detector maintains a lightweight set of observed values per monitored field and emits an alert when a value not present in the set is seen for the first time (subject to configuration).

## Configuration arguments

Only parameters specific to this detector are listed below -- see [Common parameters](../detectors.md#common-parameters-all-detectors) and [Variable detector parameters](../detectors.md#variable-detector-parameters) in the Detectors overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|new_value_detector|Indicates what type of method it is.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: new_value_detector
        auto_config: true
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            parser: PARSER
            global_instances: {}
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/new_value.py:example"
```

Go back [Index](../index.md)
