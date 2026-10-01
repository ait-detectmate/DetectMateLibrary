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

## Examples

Set up the parser (parsing requires a valid API key):

```python
--8<-- "docs/examples/parsers/logbatcher_parser.py:basic"
```

Using a local Ollama instance:

```python
--8<-- "docs/examples/parsers/logbatcher_parser.py:ollama"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/parsers/logbatcher_parser.yaml"
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
    | `method_type` | string | logbatcher_parser | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `model` | string | gpt-4o-mini | specific | fitting description yet to find |
    | `api_key` | string |  | specific | fitting description yet to find |
    | `base_url` | string |  | specific | fitting description yet to find |
    | `batch_size` | integer | 10 | specific | fitting description yet to find |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `log_format` | string, null | None | shared | fitting description yet to find |
    | `time_format` | string, null | None | shared | fitting description yet to find |
<!-- End arguments -->
