# Drain Parser [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/parsers/drain.py)]

The parser is derived from the official [Drain publication](https://ieeexplore.ieee.org/document/8029742).

It also wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. When parsing large numbers of log lines in non-stream (batch) mode, it is recommended to use the performance-oriented implementation.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |


| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ✅  | ❌  | ✅ |

!!! warning "Not yet stable"
    This parser is not yet in a stable release and may behave differently across platforms or hardware.

## Examples

Templates are kept when training resumes (default):

```python title="Example"
--8<-- "docs/examples/parsers/drain_parser.py:example_1"
```

Templates are reset after each training round (`reset_in_post_train: true`):

```python title="Reset example"
--8<-- "docs/examples/parsers/drain_parser.py:example_2"
```

## Configuration file

The configuration used by the examples above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml title="Configuration"
--8<-- "docs/examples/parsers/drain_parser.yaml"
```

The same file works unchanged in both places a parser runs:

- **Library**: load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `parsers:` must match the parser's `name`.
- **[DetectMateService](https://github.com/ait-detectmate/DetectMateService)**: use it as the service's parser configuration.

## Configuration arguments

Arguments are grouped by YAML block. **Scope** identifies fields specific to Drain and fields inherited from the parser generator base. When Drain overrides an inherited default, the base default appears in parentheses. [Shared parser generator parameters](../parsers.md#parser-generators)

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
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | shared | Add a connector to the output schema. |
    | `connector_url` | string, null | None | shared | Set up the URL of the connector for the output schema. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
    | `log_source` | string, null | None | shared | Process only inputs of the same log source. |
    | `reset_in_post_train` | boolean | False | shared | Clear buffered training logs after generating templates. |
    | `Finetune` | array | [['depth', [1, 2, 3, 4]], ['max_childs', [10, 40]], ['sim_thres', [0.2, 0.4, 0.6, 0.8]]] (shared: []) | shared | Candidate [parameter, values] pairs for automatic configuration. |
<!-- End arguments -->
