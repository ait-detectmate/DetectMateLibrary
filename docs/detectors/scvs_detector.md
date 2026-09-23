# SCVS Detector

The Sequence Count Vector Set Detector (SCVS) detects anomalies by finding count vectors that were not present in the training dataset.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

A count vector is formed by counting the number of appearances of each event ID in a sequence of a specific window size.

Count vectors learned during training are stored via [persistency](../auxiliar/persistency.md), so a trained model can be saved and restored with a `persist:` block. A count vector is only comparable within the window it was counted over, so restoring state at a different `window_size` logs a warning  --  the restored vectors cannot match and every window would alert.

## Configuration arguments
✅ Federation compatible (Binary not available).

Only parameters specific to this detector are listed below -- see [Common parameters](../detectors.md#common-parameters-all-detectors) in the Detectors overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|scvs_detector|Indicates what type of method it is.|
|window_size|integer|10|Length of the event-ID window a count vector is built over.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: scvs_detector
        auto_config: true
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            parser: PARSER
            global_instances: {}
            window_size: 10
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/scvs_detector.py:example"
```

Go back [Index](../index.md)
