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

All parameters this detector accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this detector or `shared` with other detectors (see the [Detectors overview](../detectors.md#common-parameters-all-detectors)). Where this detector changes a shared default, the shared value is shown in brackets.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | deeplog_detector | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | True | shared | Runs the configuration step before the training process. |
    | `events` | object | {} | shared | Events configuration dict keyed by event_id. |
    | `global` | object | {} | shared | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |
    | `persist` | object, null | None | shared | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See the Persistency page. |

??? note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `parser` | string | PARSER | shared | Name of the parser used. |
    | `window_size` | integer | 10 | shared | Number of consecutive events used as one training/detection sequence. |
    | `validation_per` | number | 0.2 | shared | Fraction of data held out for validation during (fine)training. |
    | `finetune_epochs` | integer | 2 | shared | Number of epochs used when finetuning during the configuration phase. |
    | `hyperparameters` | object | {'Model': {'hidden_dim': 64, 'n_layers': 2}, 'Train': {'seed': 0, 'batch_size': 2048, 'learning_rate': 0.01, 'epochs': 10, 'patience': 3}, 'Finetune': [['Model', 'hidden_dim', [128, 256, 512]], ['Model', 'n_layers', [1, 2, 3]], ['Train', 'learning_rate', [0.01, 0.02, 0.03]]]} | shared | Model, training and hyperparameter-search settings for the DeepLog model. |
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
