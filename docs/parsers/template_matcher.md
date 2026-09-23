# Template matcher

The template matcher is a parser that takes a set of templates and matches them to incoming logs. It extracts parameters from positions marked with the <*> wildcard and returns a ParserSchema with the matched template and the extracted variables.

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

## Configuration arguments

Only parameters specific to this parser are listed below -- see [Common parameters](../parsers.md#common-parameters-all-parsers) in the Parsers overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|matcher_parser|No description provided.|
|remove_spaces|boolean|True|No description provided.|
|remove_punctuation|boolean|True|No description provided.|
|lowercase|boolean|True|No description provided.|
|path_templates|string, null|None|No description provided.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
parsers:
    <COMPONENT_NAME>:
        method_type: matcher_parser
        auto_config: false
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            log_format: null
            time_format: null
            remove_spaces: true
            remove_punctuation: true
            lowercase: true
            path_templates: null
```
<!-- End config -->

### Library usage
To use it as a python script, you can follow the example below.

Simple usage  --  load templates and match a log:

```python
--8<-- "docs/examples/parsers/template_matcher.py:example"
```


Go back to [Index](../index.md)
