# Value Range Detector

The Value Range Detector raises alerts when numerical values outside of known ranges appear in configured fields. It is useful to detect unexpected changes, configuration drift, or the appearance of new actors in the environment.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |


✅ Federation compatible.

## Description

This detector maintains a lightweight set of observed values per monitored field and emits an alert when a value outside the learned range is seen (subject to configuration).

## Configuration arguments

Only parameters specific to this detector are listed below -- see [Common parameters](../detectors.md#common-parameters-all-detectors) and [Variable detector parameters](../detectors.md#variable-detector-parameters) in the Detectors overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|value_range_detector|Indicates what type of method it is.|
|ignore_non_numerical_val|boolean|True|Drop non-numeric values instead of raising when a configured variable cannot be cast to a number.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: value_range_detector
        auto_config: true
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            parser: PARSER
            global_instances: {}
            ignore_non_numerical_val: true
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/value_range.py:example"
```

Go back [Index](../index.md)
