# AECID-PG Parser [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/parsers/aecid_pg.py)]

AECID-PG counts token sequences in training logs to build a tree. It uses branch frequencies to decide which branches to merge into `<*>` wildcards, then turns the pruned tree into log templates. [AECID-PG publication](https://dl.ifip.org/db/conf/im/im2019-ws1-annet/191478.pdf)

The parser uses the template generator from DetectMatePerformance, which also provides a batch API for mining templates from collections of log lines. [DetectMatePerformance](https://github.com/ait-detectmate/DetectMatePerformance)

## In/out

Input and output schemas in the pipeline

|            | Schema                        | Description      |
|------------|-------------------------------|------------------|
| **Input**  | [LogSchema](../schemas.md)    | Unstructured log |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ✅ | ❌ | ✅ |

## Examples

By default, AECID-PG keeps earlier training logs when training resumes.

```python title="Example"
--8<-- "docs/examples/parsers/aecid_pg.py:example_1"
```

Run this after the first example to clear the training buffer after each round with `reset_in_post_train: true`. Once retraining finishes, the new template matches and the earlier template is gone.

```python title="Reset example"
--8<-- "docs/examples/parsers/aecid_pg.py:example_2"
```

## Configuration file

This file sets the initial training size to two logs. Setting `theta_1` to `0.6` merges the two equally frequent rank tokens into a wildcard. See [Configuration arguments](#configuration-arguments) for the remaining defaults.

```yaml title="Configuration"
--8<-- "docs/examples/parsers/aecid_pg.yaml"
```

- **Library**. Load this file with `yaml.safe_load` and pass the result as `config=`. The key under `parsers` must match the parser's `name`.
- **DetectMateService**. Use this file as the component configuration with a library version that includes AECID-PG. In the service settings, set `component_type` to `parsers.aecid_pg.AECIDPGParser` and `component_config_class` to `parsers.aecid_pg.AECIDPGConfig`. [DetectMateService](https://github.com/ait-detectmate/DetectMateService)

## Configuration arguments

Arguments are grouped by YAML block. **Scope** identifies fields specific to AECID-PG and fields inherited from the parser generator base. When AECID-PG overrides an inherited default, the base default appears in parentheses. [Shared parser generator parameters](../parsers.md#parser-generators)

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | aecid_pg_parser | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `theta_1` | number | 0.2 | specific | Minimum relative branch frequency for a branch to count as common. |
    | `theta_2` | number | 0.8 | specific | Merge branches below this frequency when the combined frequency of common branches is below theta_3. |
    | `theta_3` | number | 0.5 | specific | Minimum combined frequency of common branches needed to merge the remaining branches. |
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
    | `Finetune` | array | [['theta_1', [0.01, 0.05, 0.1, 0.2]], ['theta_2', [0.7, 0.8, 0.9]], ['theta_3', [0.4, 0.5, 0.6]]] (shared: []) | shared | Candidate [parameter, values] pairs for automatic configuration. |
<!-- End arguments -->
