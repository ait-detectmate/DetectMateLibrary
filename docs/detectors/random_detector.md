# Random Detector

The Random Detector inspects incoming ParserSchema instances and, according to its configuration, emits alerts with synthetic content. It can be configured to sample specific log variables, set thresholds or control alert frequency. Use it for integration testing, load testing, or as a simple example of a detector implementation.

## In/out

Input and output schemas in the pipeline

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Generated alerts |

## Configuration arguments

Arguments used in the initalization of the component.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|random_detector|Indicates what type of method is.|
|auto_config|boolean|True|Runs the configuration step before the training process.|
|start_id|integer|10|Number use to start the unique ID generator.|
|data_use_training|integer, null|None|Data use for training, if None, training is not done.|
|data_use_configure|integer, null|None|Data use for configuration, if None, configuration is not done.|
|use_config_data_as_training|boolean|True|Combine the configure data in the training process if True.|
|parser|string|PARSER|Name of the parser used.|
|events|object|{}|Events configuration dict keyed by event_id.|
|global_instances|object|{}|Configuration for a specific instance within an event.|
<!-- End arguments -->

## Examples

Examples to use the component in the DetectMate environment.

## Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example bellow.

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

## Library usage

To use it as a python script, you can follow the example bellow.

```python
--8<-- "docs/examples/detectors/random_detector.py:example"
```

Go back [Index](../index.md)
