# Auto Parser

The auto parser uses a brute-force strategy: it iterates through every log-type record in the internal dataset and chooses the regex and templates that best matches the provided logs.

Compared with Template Matcher approaches, its key benefit is that you don’t need to supply templates or regex formatting during initialization, which makes it more convenient for rapid deployments. Its main drawback is that it only performs well for log types that are already included in the internal dataset.

The built-in dataset of log types cannot be modified by users and currently supports: HDFS, BGL, Audit, Syslog, OpenVPN, DNSmasq, and Apache.

It wraps functionality from the [DetectMatePerformance project](https://github.com/ait-detectmate/DetectMatePerformance).

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Configuration arguments

Only parameters specific to this parser are listed below -- see [Common parameters](../parsers.md#common-parameters-all-parsers) in the Parsers overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|auto_parser|fitting description yet to find|
|fix_type|string||fitting description yet to find|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
parsers:
    <COMPONENT_NAME>:
        method_type: auto_parser
        auto_config: false
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            log_format: null
            time_format: null
            fix_type: ''
```
<!-- End config -->

### Library usage
To use it as a python script, you can follow the example below.

Without fixing log type:

```python
--8<-- "docs/examples/parsers/auto_parser.py:example_1"
```

With fixing log type:

```python
--8<-- "docs/examples/parsers/auto_parser.py:example_2"
```

Go back to [Index](../index.md)
