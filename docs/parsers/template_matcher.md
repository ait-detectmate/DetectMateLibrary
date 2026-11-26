# Template Matcher [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/parsers/template_matcher/_parser.py)]

The Template Matcher matches predefined templates to incoming logs. It extracts parameters from positions marked with `<*>` and returns a `ParserSchema` with the matched template and extracted variables.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ❌ | ❌  | ❌  | ❌ |

## Overview

The template matcher is a lightweight, fast parser intended for logs that follow stable textual templates with variable fields. Templates use the token `<*>` to mark wildcard slots. The matcher:

- Preprocesses logs and templates according to the configured spacing, punctuation, and case options.
- Tries the templates in order of how often each has matched so far, uses the first one that matches, and extracts all wildcard parameters in order. If templates overlap, the same log can therefore get a different `eventID` over time.
- Populates `eventID`, `template`, `variables`, `logID`, and related `ParserSchema` fields.
- **`eventID` is the 0-indexed line number of the matched template** in the template file (first line → `eventID: 0`, second line → `eventID: 1`, etc.).

This parser is designed for high-throughput use when templates are known in advance.

## EventID assignment (preliminary)

The `eventID` (or `event_id`) field in the output `ParserSchema` identifies which template was matched. It equals the **0-indexed line number** of the matching template in the template file, for example:

| Line in template file | EventID |
|-----------------------|---------|
| 1st line              | 0       |
| 2nd line              | 1       |
| 3rd line              | 2       |
| ...                   | ...     |

The `eventID` is the integer key used in detector configurations (e.g., `NewValueDetector`) to scope detection rules to logs of a particular template type.

## Template format

- Templates are plain text lines in a template file.
- Templates use `<*>` for wildcard slots.

Example template file (templates.txt):
```text
pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>
login success: user=<*> source=<*>
```

Templates can also name their wildcards (`<user>` instead of `<*>`), and a `.csv` template
file with an `EventId` column can name each template. Detector configurations can then use
these names instead of numbers; see
[Named EventIDs and variables](../detectors.md#named-eventids-and-variables).

## Example

Load the templates and match a log:

```python title="Example"
--8<-- "docs/examples/parsers/template_matcher.py:example"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml title="Configuration"
--8<-- "docs/examples/parsers/template_matcher.yaml"
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
    | `method_type` | string | matcher_parser | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `remove_spaces` | boolean | True | specific | Remove duplicate spaces. |
    | `remove_punctuation` | boolean | True | specific | Remove punctuation. |
    | `lowercase` | boolean | True | specific | Convert text to lowercase. |
    | `path_templates` | string, null | None | specific | Path of the templates file. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Reuse configuration records as training data. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | shared | Add a connector to the output schema. |
    | `connector_url` | string, null | None | shared | Set up the URL of the connector for the output schema. |
    | `log_format` | string, null | None | shared | Pattern with named fields such as `<Time>` and `<Content>` for splitting a raw log. |
    | `time_format` | string, null | None | shared | Format used to parse the timestamp field. |
    | `log_source` | string, null | None | shared | Process only inputs of the same log source. |
<!-- End arguments -->
