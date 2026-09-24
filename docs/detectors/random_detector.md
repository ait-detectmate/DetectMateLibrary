# Random Detector

The Random Detector inspects incoming ParserSchema instances and, according to its configuration, emits alerts with synthetic content. It can be configured to sample specific log variables, set thresholds or control alert frequency. Use it for integration testing, load testing, or as a simple example of a detector implementation.

## In/out

Input and output schemas in the pipeline

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Generated alerts |

## Configuration arguments

Only parameters specific to this detector are listed below -- see [Common parameters](../detectors.md#common-parameters-all-detectors) in the Detectors overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|random_detector|Indicates what type of method it is.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: random_detector
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
--8<-- "docs/examples/detectors/random_detector.py:example"
```

Go back [Index](../index.md)
