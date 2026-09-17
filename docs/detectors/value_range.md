# Value Range Detector

The Value Range Detector raises alerts when numerical values outside of known ranges appear in configured fields. It is useful to detect unexpected changes, configuration drift, or the appearance of new actors in the environment.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

This detector maintains a lightweight set of observed values per monitored field and emits an alert when a value outside the learned range is seen (subject to configuration).

## Configuration arguments

Arguments used in the initalization of the component.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|value_range_detector|Indicates what type of method it is.|
|auto_config|boolean|True|Runs the configuration step before the training process.|
|start_id|integer|10|Number use to start the unique ID generator.|
|data_use_training|integer, null|None|Data use for training, if None, training is not done.|
|data_use_configure|integer, null|None|Data use for configuration, if None, configuration is not done.|
|use_config_data_as_training|boolean|True|Combine the configure data in the training process if True.|
|parser|string|PARSER|Name of the parser used.|
|events|object|{}|Events configuration dict keyed by event_id.|
|global_instances|object|{}|Configuration for a specific instance within an event.|
|use_stable_vars|boolean|True|Select variables classified as STABLE when auto-configuring.|
|use_static_vars|boolean|True|Select variables classified as STATIC when auto-configuring.|
|stability_segmentation|string|count|How to segment values for stability classification. 'count' cuts segments at equal sample counts (the historical behaviour), 'time' cuts them at equal durations instead, and 'both' requires the variable to pass under both segmentations. The time-aware modes need timestamp_variable to be set.|
|timestamp_variable|string, null|None|Name of the log field holding the event timestamp, read from the record's logFormatVariables. Required by the 'time'/'both' stability segmentation modes.|
|timestamp_format|string, null|None|Expected format of timestamp_variable. If None, the format is auto-detected.|
|ignore_non_numerical_val|boolean|True|Drop non-numeric values instead of raising when a configured variable cannot be cast to a number.|
<!-- End arguments -->

## Examples
Examples to use the component in the DetectMate environment.
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
            use_stable_vars: true
            use_static_vars: true
            stability_segmentation: count
            timestamp_variable: null
            timestamp_format: null
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
