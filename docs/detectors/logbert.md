# LogBert Detector

The LogBert Detector is inspired from [LogBert paper](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=9534113).

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
|method_type|string|logbert_detector|Indicates what type of method it is.|
|hyperparameters|object|{'Model': {'n_embed': 10, 'hidden': 32, 'num_heads': 2, 'n_layers': 1, 'dropout': 0.0, 'max_len': 1000}, 'Train': {'seed': 0, 'batch_size': 256, 'learning_rate': 0.01, 'epochs': 10, 'mask_per': 0.4, 'alpha': 0.0, 'patience': 3}, 'Finetune': [['Model', 'hidden', [64, 128, 256]], ['Model', 'n_layers', [1, 2, 3]], ['Train', 'learning_rate', [0.002, 0.001, 0.005]]]}|Model, training and hyperparameter-search settings for the LogBERT model.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: logbert_detector
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
                    n_embed: 10
                    hidden: 32
                    num_heads: 2
                    n_layers: 1
                    dropout: 0.0
                    max_len: 1000
                Train:
                    seed: 0
                    batch_size: 256
                    learning_rate: 0.01
                    epochs: 10
                    mask_per: 0.4
                    alpha: 0.0
                    patience: 3
                Finetune:
                -   - Model
                    - hidden
                    -   - 64
                        - 128
                        - 256
                -   - Model
                    - n_layers
                    -   - 1
                        - 2
                        - 3
                -   - Train
                    - learning_rate
                    -   - 0.002
                        - 0.001
                        - 0.005
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/logbert_detector.py:example"
```

Go back [Index](../index.md)
