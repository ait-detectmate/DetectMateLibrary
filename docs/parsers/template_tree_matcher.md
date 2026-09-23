# Template Tree Matcher

The Template Tree Matcher is a parser that matches incoming logs against a set of templates using a tree-based depth-first search. It provides faster matching for batch workloads compared with the streaming Template Matcher.

This parser wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. Prefer  use the performance implementation when parsing many log lines in non-stream (batch) mode.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

WARNING: This parser is not yet in a stable release and may behave differently across platforms or hardware.

## Template format

- Templates are plain text lines in a template file.
- Use the token `<*>` to mark wildcard slots.

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

Note: this matcher removes non-alphanumeric characters from logs and templates before matching, except for the `<*>` token. Ensure your templates are compatible with that normalization.

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

```python
--8 < --"docs/examples/parsers/template_tree_matcher.py"
```

Go back to [Index](../index.md)
