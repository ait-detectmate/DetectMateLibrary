# LogBatcher Parser

LLM-based log parser that infers event templates from raw log messages using any OpenAI-compatible model. No training data or labeled examples are required.

## In/out

Input and output schemas in the pipeline

|            | Schema                        | Description                              |
|------------|-------------------------------|------------------------------------------|
| **Input**  | [LogSchema](../schemas.md)    | Raw log string                           |
| **Output** | [ParserSchema](../schemas.md) | Structured log with template and variables |

## Installation

`LogBatcherParser` requires the `llm` optional extra:

```bash
pip install "detectmatelibrary[llm]"
# or with uv
uv sync --extra llm
```

## Overview

`LogBatcherParser` wraps the [LogBatcher](https://github.com/LogIntelligence/LogBatcher) engine (MIT, LogIntelligence 2024) as a `CoreParser`. Parsing proceeds in two phases:

1. **Cache lookup**  --  the incoming log is matched against previously seen templates using a hash-based exact match followed by a tree-based similarity check. If a match is found, no LLM call is made.
2. **LLM query**  --  on a cache miss, the log is submitted to the configured model. The returned template is stored in the cache for future reuse.

Variable slots in templates use the `<*>` wildcard notation (e.g. `User <*> logged in from <*>`). Extracted variables are written to `output_["variables"]` in order of appearance.

## Configuration arguments

Only parameters specific to this parser are listed below -- see [Common parameters](../parsers.md#common-parameters-all-parsers) in the Parsers overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|model|string|gpt-4o-mini|fitting description yet to find|
|api_key|string||fitting description yet to find|
|base_url|string||fitting description yet to find|
|batch_size|integer|10|fitting description yet to find|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
parsers:
    <COMPONENT_NAME>:
        method_type: logbatcher_parser
        auto_config: false
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            log_format: null
            time_format: null
            model: gpt-4o-mini
            api_key: ''
            base_url: ''
            batch_size: 10
```
<!-- End config -->


### Library usage
To use it as a python script, you can follow the example below.
Basic usage  --  set up the parser (parsing requires a valid API key):

```python
--8<-- "docs/examples/parsers/logbatcher_parser.py:basic"
```

Using a local Ollama instance:

```python
--8<-- "docs/examples/parsers/logbatcher_parser.py:ollama"
```

Passing config as a dict:

```python
--8<-- "docs/examples/parsers/logbatcher_parser.py:config"
```

Go back to [Index](../index.md)
