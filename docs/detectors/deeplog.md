# Deeplog Detector

The Deeplog Detector is inspired from [Deeplog paper](https://dl.acm.org/doi/10.1145/3133956.3134015).

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Combined alert / finding |

## Description
Deep learning method that looks at the event ID sequence

## Configuration

```yaml
detectors:
    DeeplogDetector:
        method_type: deeplog_detector
        auto_config: False
        data_use_training: 10
        window_size: 3
        hyperparameters:
            Model: 
                hidden_dim: 64
                n_layers: 2
            Train: 
                seed: 0
                batch_size: 2048
                learning_rate: 0.01
                epochs: 10
                patience: 3
            Finetune: 
                - ["Model", "hidden_dim", [128, 256, 512]]
                - ["Model", "n_layers", [1, 2, 3]]
                - ["Train", "learning_rate", [0.01, 0.02, 0.03]]
```

## Example usage

```python
--8<-- "docs/examples/detectors/deeplog_detector.py:example"
```
Go back [Index](../index.md)
