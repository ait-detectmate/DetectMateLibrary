# AlertBERT Alert Aggregation

The AlertBERT alert aggregator implements alert aggregation by grouping alerts according to their time-differences and embeddings of them obtained through masked-language-models, as proposed by [Karner et al.](https://doi.org/10.48550/arXiv.2602.06534).

## In/out

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](../schemas.md) | Aggregated alerts    |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ❌ | ❌ | ❌ |

## Description

This class implements alert aggregation by considering the differences between the timestamps of alerts and embeddings of alerts created by masked-language-models.

To this end, the method has two threshold parameters $\delta$ and $\theta$.
Two alerts will be assigned to the same group if the time difference between them is $\leq\delta$ and the cosine distance of their embeddings is $\leq\delta/\theta$.
The time difference is computed based on the timestamps of the last logs associated with each alert as these determine the earliest time at which the alert was detected.
Important: It is assumed that the alerts arrive in order of their timestamps!

To obtain the embeddings, in the configuration one can either specify the path of a saved masked-language-model, or one can specify the number of alerts to use as training data and the features of the alerts to use as input to the model.
Optionally, it is possible to add features to alerts in a pre-processing step by assigning them to the field `alert['alertDetails']['<feature-name>']`, which can then be specified in the configuration as `'alertDetails:<feature-name>`.

## Example

```python
--8<-- "docs/examples/alert_aggregators/alertbert.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/alert_aggregators/alertbert.yaml"
```

Load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `alert_aggregators:` must match the aggregator's `name`.

## Configuration arguments

All parameters this alert aggregator accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this aggregator or `shared` with other alert aggregators.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | AlertBERT_aggregator | shared | The type of the aggregation method. Defaults to 'AlertBERT_aggregator'. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `buffer_size` | integer | 1000 | specific | The size of the buffer. Defaults to 1000. |
    | `buffer_mode` | object | BufferMode.BATCH | specific | The mode of the buffer. Defaults to 'BATCH'. |
    | `delta` | number | 10.0 | specific | The threshold for the clustering. Defaults to 10.0. |
    | `model_id` | string | AlertBERT_aggregator_2026-11-03T17:08:16.062231 | specific | The unique identifier of the model. Defaults to 'AlertBERT_aggregator_<current_datetime>'. |
    | `path` | string | alertbert_models | specific | The path to the save location of the AlertBERT model. Defaults to 'alertbert_models'. |
    | `train_model` | boolean | True | specific | Whether to train the AlertBERT model. If False, the model will be loaded from disk. Defaults to False. |
    | `save_model` | boolean | True | specific | Whether to save the trained AlertBERT model to disk. Defaults to True. |
    | `theta` | number | 20.0 | specific | The parameter for the time-cosine-distance. Defaults to 20.0. |
    | `dim_reduction` | integer | 2 | specific | The dimension to which the alert embeddings will be reduced via PCA before clustering. Defaults to 2. |
    | `clustering_backend` | string | detectmate | specific | The backend to use for clustering. The option "detectmate" uses the implementation inherited from the parent class, the option "scipy" uses the implementation of the AlertBERT model. Defaults to "detectmate". |
    | `layers` | array | ('embedding', 'encoder') | specific | The layers of the AlertBERT model to use for obtaining the alert embeddings. Defaults to ("embedding", "encoder"). |
    | `train_size` | integer | 50000 | specific | The number of alerts to use for training the AlertBERT model. Defaults to 50000. |
    | `val_size` | integer | 10000 | specific | The number of alerts to use for validation during training of the AlertBERT model. Defaults to 10000. |
    | `skip_first` | integer | 0 | specific | The number of alerts to skip before starting to collect alerts for training the AlertBERT model. Defaults to 0. |
    | `min_freq` | integer | 10 | specific | The minimum frequency of tokens to be included in the vocabulary of the AlertBERT model. Defaults to 10. |
    | `features` | array | ('description',) | specific | The keys of fields of the alerts to use as features for training the AlertBERT model. Fields within the 'alertDetails' field can be accessed by the syntax 'alertDetails:fieldName'. Defaults to ("description",). |
    | `encoding` | string | relevantTimestamp | specific | The features of the alerts to use for rotary positional encoding. Defaults to "relevantTimestamp". |
    | `n_heads` | integer | 4 | specific | The number of attention heads in the AlertBERT model. Defaults to 4. |
    | `dim_per_head` | integer | 16 | specific | The dimensionality of each attention head in the AlertBERT model. Defaults to 16. |
    | `num_layers` | integer | 1 | specific | The number of layers in the model in the AlertBERT model. Defaults to 1. |
    | `feedforward_factor` | integer | 4 | specific | The factor by which the feedforward dimension is larger than the model dimension in the AlertBERT model. Defaults to 4. |
    | `rotary_max_exp` | integer | 14 | specific | The maximum exponent for the rotary positional encoding in the AlertBERT model. Defaults to 14. |
    | `rotary_cutoff` | number | 0.75 | specific | The cutoff for the rotary positional encoding in the AlertBERT model. Defaults to 0.75. |
    | `context_size` | integer | 1024 | specific | The context size for the AlertBERT model. Defaults to 1024. |
    | `batch_size` | integer | 8 | specific | The batch size for training the AlertBERT model. Defaults to 8. |
    | `updates` | array | (240, 300) | specific | The number of updates for training the AlertBERT model. Defaults to (240, 300). |
    | `lr` | number | 0.005 | specific | The learning rate for training the AlertBERT model. Defaults to 5e-3. |
    | `warm_up_steps` | integer | 20 | specific | The number of warm-up steps for training the AlertBERT model. Defaults to 100. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
<!-- End arguments -->
