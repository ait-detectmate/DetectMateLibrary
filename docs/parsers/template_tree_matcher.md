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

All parameters this parser accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this parser or `shared` with other parsers (see the [Parsers overview](../parsers.md#common-parameters-all-parsers)).

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | tree_matcher | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `path_templates` | string, null | None | specific | fitting description yet to find |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
<!-- End arguments -->

Note: this matcher removes non-alphanumeric characters from logs and templates before matching, except for the `<*>` token. Ensure your templates are compatible with that normalization.

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
parsers:
    <COMPONENT_NAME>:
        method_type: tree_matcher
        auto_config: false
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            log_format: null
            time_format: null
            path_templates: null
```
<!-- End config -->

### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/parsers/template_tree_matcher.py"
```

Go back to [Index](../index.md)
