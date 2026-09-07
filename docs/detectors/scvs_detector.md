# SCVS Detector

The Sequence Count Vector Set Detector (SCVS) detects anomalies by finding count vectors that were not present in the training dataset.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

A count vector is formed by counting the number of appearance of each event ID in a sequence of a specific window size.

Count vectors learned during training are stored via [persistency](../auxiliar/persistency.md), so a trained model can be saved and restored with a `persist:` block. A count vector is only comparable within the window it was counted over, so restoring state at a different `window_size` logs a warning — the restored vectors cannot match and every window would alert.


## Configuration example

```yaml
detectors:
    SCVSDetector:
        method_type: scvs_detector
        window_size: 10
```


## Example usage

```python
--8<-- "docs/examples/detectors/scvs_detector.py:example"
```

Go back [Index](../index.md)
