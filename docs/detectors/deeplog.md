# Deeplog Detector

The Deeplog Detector is inspired from [Deeplog paper](https://dl.acm.org/doi/10.1145/3133956.3134015).

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Combined alert / finding |

## Description

Deep learning method that looks at the event ID sequence.

## Configuration arguments

Only parameters specific to this detector are listed below -- see [Common parameters](../detectors.md#common-parameters-all-detectors) and [Deep learning detector parameters](../detectors.md#deep-learning-detector-parameters) in the Detectors overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|deeplog_detector|Indicates what type of method it is.|
|hyperparameters|object|{'Model': {'hidden_dim': 64, 'n_layers': 2}, 'Train': {'seed': 0, 'batch_size': 2048, 'learning_rate': 0.01, 'epochs': 10, 'patience': 3}, 'Finetune': [['Model', 'hidden_dim', [128, 256, 512]], ['Model', 'n_layers', [1, 2, 3]], ['Train', 'learning_rate', [0.01, 0.02, 0.03]]]}|Model, training and hyperparameter-search settings for the DeepLog model.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: deeplog_detector
        auto_config: true
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            parser: PARSER
            global_instances: {}
            window_size: 10
            validation_per: 0.2
            finetune_epochs: 2
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
                -   - Model
                    - hidden_dim
                    -   - 128
                        - 256
                        - 512
                -   - Model
                    - n_layers
                    -   - 1
                        - 2
                        - 3
                -   - Train
                    - learning_rate
                    -   - 0.01
                        - 0.02
                        - 0.03
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/deeplog_detector.py:example"
```

Go back [Index](../index.md)
