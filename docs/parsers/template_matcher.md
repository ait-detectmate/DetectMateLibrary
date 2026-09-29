# Template Matcher

The Template Matcher is a parser that takes a set of templates and matches them to incoming logs. It extracts parameters from positions marked with the <*> wildcard and returns a ParserSchema with the matched template and the extracted variables.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Overview

The template matcher is a lightweight, fast parser intended for logs that follow stable textual templates with variable fields. Templates use the token `<*>` to mark wildcard slots. The matcher:

- Preprocesses logs and templates (remove spaces, punctuation, lowercase) based on config.
- Finds the first template that matches and extracts all wildcard parameters in order.
- Populates ParserSchema fields: `EventID`, `template`, `variables`,  `logID`, and related fields.
- **`EventID` is the 0-indexed line number of the matched template** in the template file (first line → `EventID: 0`, second line → `EventID: 1`, etc.).

This parser is deterministic and designed for high-throughput use when templates are known in advance.

## EventID assignment (preliminary)

The `EventID` (or `event_id`) field in the output `ParserSchema` identifies which template was matched. It equals the **0-indexed line number** of the matching template in the template file, for example:

| Line in template file | EventID |
|-----------------------|---------|
| 1st line              | 0       |
| 2nd line              | 1       |
| 3rd line              | 2       |
| ...                   | ...     |

The `EventID` is the integer key used in detector configurations (e.g., `NewValueDetector`) to scope detection rules to logs of a particular template type.

## Template format

- Templates are plain text lines in a template file.
- Templates use `<*>` for wildcard slots.

Example template file (templates.txt):
```text
pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>
login success: user=<*> source=<*>
```

## Example

Load the templates and match a log:

```python
--8<-- "docs/examples/parsers/template_matcher.py:example"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
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
    | `remove_spaces` | boolean | True | specific | fitting description yet to find |
    | `remove_punctuation` | boolean | True | specific | fitting description yet to find |
    | `lowercase` | boolean | True | specific | fitting description yet to find |
    | `path_templates` | string, null | None | specific | fitting description yet to find |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
<!-- End arguments -->
