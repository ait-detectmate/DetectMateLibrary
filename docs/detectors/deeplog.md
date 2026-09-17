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

Arguments used in the initalization of the component.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|deeplog_detector|Indicates what type of method it is.|
|auto_config|boolean|True|Runs the configuration step before the training process.|
|start_id|integer|10|Number use to start the unique ID generator.|
|data_use_training|integer, null|None|Data use for training, if None, training is not done.|
|data_use_configure|integer, null|None|Data use for configuration, if None, configuration is not done.|
|use_config_data_as_training|boolean|True|Combine the configure data in the training process if True.|
|parser|string|PARSER|Name of the parser used.|
|events|object|{}|Events configuration dict keyed by event_id.|
|global_instances|object|{}|Configuration for a specific instance within an event.|
|window_size|integer|10|Number of consecutive events used as one training/detection sequence.|
|validation_per|number|0.2|Fraction of data held out for validation during (fine)training.|
|finetune_epochs|integer|2|Number of epochs used when finetuning during the configuration phase.|
|hyperparameters|object|{'Model': {'hidden_dim': 64, 'n_layers': 2}, 'Train': {'seed': 0, 'batch_size': 2048, 'learning_rate': 0.01, 'epochs': 10, 'patience': 3}, 'Finetune': [['Model', 'hidden_dim', [128, 256, 512]], ['Model', 'n_layers', [1, 2, 3]], ['Train', 'learning_rate', [0.01, 0.02, 0.03]]]}|Model, training and hyperparameter-search settings for the DeepLog model.|
<!-- End arguments -->

## Examples
Examples to use the component in the DetectMate environment.
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
