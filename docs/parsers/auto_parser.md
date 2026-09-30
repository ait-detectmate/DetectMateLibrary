# Auto Parser

The Auto Parser uses a brute-force strategy: it iterates through every log-type record in the internal dataset and chooses the regex and templates that best matches the provided logs.

Compared with Template Matcher approaches, its key benefit is that you don’t need to supply templates or regex formatting during initialization, which makes it more convenient for rapid deployments. Its main drawback is that it only performs well for log types that are already included in the internal dataset.

The built-in dataset of log types cannot be modified by users and currently supports: HDFS, BGL, Audit, Syslog, OpenVPN, DNSmasq, and Apache.

It wraps functionality from the [DetectMatePerformance project](https://github.com/ait-detectmate/DetectMatePerformance).

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Examples

Without fixing log type:

```python
--8<-- "docs/examples/parsers/auto_parser.py:example_1"
```

With fixing log type:

```python
--8<-- "docs/examples/parsers/auto_parser.py:example_2"
```

## Configuration file

The configuration used by the examples above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/parsers/auto_parser.yaml"
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
    | `method_type` | string | auto_parser | shared | fitting description yet to find |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `fix_type` | string |  | specific | fitting description yet to find |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
<!-- End arguments -->
