# Rule Detector

The Rule Detector raises alerts based on a configurable set of rules.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ❌ | ❌ | ❌ | ❌ |

## Description

The detector analyzes parsed logs one by one and checks which rules are triggered. When alerts are produced, the triggered rules and their messages are recorded in the `alertsObtain` field of the output schema. The `score` field contains the number of rules that triggered.

### Available rules

| Rule name | Description | Requires arguments | Enabled by default |
|---|---|---:|:---:|
| **R001 - TemplateNotFound** | Check whether the parser assigned a template to the log | No | Yes |
| **R002 - SpecificKeyword** | Check for one or more user-specified keywords in the log content | list of words | No |
| **R003 - CheckForExceptions** | Check for words commonly associated with exceptions or failures | No | Yes |
| **R004 - ErrorLevelFound** | If a Level field exists, check whether it indicates an error level | No | Yes |

Notes on table columns:

- **Rule name**: Identifier used in configuration.
- **Description**: What the rule checks.
- **Requires arguments**: Whether the rule needs additional arguments.
- **Enabled by default**: Whether the rule is active when not explicitly overridden.

## Example

```python
--8<-- "docs/examples/detectors/rule_based.py:example"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/detectors/rule_based.yaml"
```

The same file works unchanged in both places a detector runs:

- **Library**: load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `detectors:` must match the detector's `name`.
- **[DetectMateService](https://github.com/ait-detectmate/DetectMateService)**: use it as the service's detector configuration.

## Configuration arguments

All parameters this detector accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this detector or `shared` with other detectors (see the [Detectors overview](../detectors.md#common-parameters-all-detectors)). Where this detector changes a shared default, the shared value is shown in brackets.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | rule_detector | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | True | shared | Runs the configuration step before the training process. |
    | `events` | object | {} | shared | Events configuration dict keyed by event_id. |
    | `global` | object | {} | shared | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |
    | `persist` | object, null | None | shared | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See the Persistency page. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `rules` | array | [{'rule': 'R001 - TemplateNotFound'}, {'rule': 'R003 - CheckForExceptions'}, {'rule': 'R004 - ErrorLevelFound'}] | specific | List of rules to evaluate, each a dict with a 'rule' name and an optional 'args' list. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `parser` | string | PARSER | shared | Name of the parser used. |
<!-- End arguments -->
