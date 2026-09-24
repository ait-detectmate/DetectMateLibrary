# JSON Parser

Extracts structured information from JSON-formatted logs. Optionally delegates parsing of a specific JSON field (the "content") to a sibling Template Matcher parser. Nested JSON objects are always flattened to dot-separated keys in `logFormatVariables`.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Raw log (JSON string) |
| **Output** | [ParserSchema](../schemas.md) | Structured log with extracted fields |

## Configuration arguments

Only parameters specific to this parser are listed below -- see [Common parameters](../parsers.md#common-parameters-all-parsers) in the Parsers overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|timestamp_name|string|time|fitting description yet to find|
|content_name|string|message|fitting description yet to find|
|content_parser|string|JsonMatcherParser|fitting description yet to find|
<!-- End arguments -->

The `content_parser` value is a **name**, not an inline config. The referenced parser must be defined as a separate sibling entry at the same level as `JsonParser`.

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
parsers:
    <COMPONENT_NAME>:
        method_type: json_parser
        auto_config: false
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            log_format: null
            time_format: null
            timestamp_name: time
            content_name: message
            content_parser: JsonMatcherParser
```
<!-- End config -->


### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/parsers/json_parser.py:basic"
```

Dict-based config (from YAML)  --  with template matching on the `message` field:

```python
--8<-- "docs/examples/parsers/json_parser.py:dict-based"
```

Go back [Index](../index.md)
