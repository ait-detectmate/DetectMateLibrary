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

All parameters this detector accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this detector or `shared` with other detectors (see the [Detectors overview](../detectors.md#common-parameters-all-detectors)). Where this detector changes a shared default, the shared value is shown in brackets.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | logbert_detector | shared | Indicates what type of method it is. |
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
    | `hyperparameters` | object | {'Model': {'n_embed': 10, 'hidden': 32, 'num_heads': 2, 'n_layers': 1, 'dropout': 0.0, 'max_len': 1000}, 'Train': {'seed': 0, 'batch_size': 256, 'learning_rate': 0.01, 'epochs': 10, 'mask_per': 0.4, 'alpha': 0.0, 'patience': 3}, 'Finetune': [['Model', 'hidden', [64, 128, 256]], ['Model', 'n_layers', [1, 2, 3]], ['Train', 'learning_rate', [0.002, 0.001, 0.005]]]} | shared | Model, training and hyperparameter-search settings for the LogBERT model. |
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
