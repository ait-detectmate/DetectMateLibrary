# Drain Parser

The parser is derived from the official [Drain publication](https://ieeexplore.ieee.org/document/8029742).

It also wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. When parsing large numbers of log lines in non-stream (batch) mode, it is recommended to use the performance-oriented implementation.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Examples

Templates are kept when training resumes (default):

```python
--8<-- "docs/examples/parsers/drain_parser.py:example_1"
```

Templates are reset after each training round (`reset_in_post_train: true`):

```python
--8<-- "docs/examples/parsers/drain_parser.py:example_2"
```

## Configuration file

The configuration used by the examples above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/parsers/drain_parser.yaml"
```

The same file works unchanged in both places a parser runs:

- **Library**: load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `parsers:` must match the parser's `name`.
- **[DetectMateService](https://github.com/ait-detectmate/DetectMateService)**: use it as the service's parser configuration.

## Configuration arguments

All parameters this parser accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this parser or `shared` with other parsers (see the [Parsers overview](../parsers.md#common-parameters-all-parsers)).

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | drain_parser | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `depth` | integer | 2 | specific | fitting description yet to find |
    | `max_childs` | integer | 10 | specific | fitting description yet to find |
    | `sim_thres` | number | 0.2 | specific | fitting description yet to find |
    | `reset_in_post_train` | boolean | False | specific | fitting description yet to find |
    | `Finetune` | array | [['depth', [1, 2, 3, 4]], ['max_childs', [10, 40]], ['sim_thres', [0.2, 0.4, 0.6, 0.8]]] | specific | fitting description yet to find |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
<!-- End arguments -->
