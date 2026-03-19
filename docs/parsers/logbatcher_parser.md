# LogBatcher Parser

LLM-based log parser that infers event templates from raw log messages using any OpenAI-compatible model. No training data or labeled examples are required.

|            | Schema                        | Description                              |
|------------|-------------------------------|------------------------------------------|
| **Input**  | [LogSchema](../schemas.md)    | Raw log string                           |
| **Output** | [ParserSchema](../schemas.md) | Structured log with template and variables |

## Overview

`LogBatcherParser` wraps the [LogBatcher](https://github.com/LogIntelligence/LogBatcher) engine (MIT, LogIntelligence 2024) as a `CoreParser`. Parsing proceeds in two phases:

1. **Cache lookup** — the incoming log is matched against previously seen templates using a hash-based exact match followed by a tree-based similarity check. If a match is found, no LLM call is made.
2. **LLM query** — on a cache miss, the log is submitted to the configured model. The returned template is stored in the cache for future reuse.

Variable slots in templates use the `<*>` wildcard notation (e.g. `User <*> logged in from <*>`). Extracted variables are written to `output_["variables"]` in order of appearance.

## Configuration

| Field | Type | Default | Description |
|---|---|---|---|
| `method_type` | string | `"logbatcher_parser"` | Parser type identifier |
| `model` | string | `"gpt-4o-mini"` | Model name passed to the OpenAI-compatible endpoint |
| `api_key` | string | `""` | API key for the chosen provider |
| `base_url` | string | `""` | Base URL of the OpenAI-compatible endpoint. Leave empty to use the default OpenAI endpoint |
| `batch_size` | int | `10` | Maximum number of logs submitted per LLM call |

Example YAML fragment (OpenAI):

```yaml
parsers:
  LogBatcherParser:
    method_type: logbatcher_parser
    params:
      model: "gpt-4o-mini"
      api_key: "<YOUR_API_KEY>"
      batch_size: 10
```

Example YAML fragment (local Ollama):

```yaml
parsers:
  LogBatcherParser:
    method_type: logbatcher_parser
    params:
      model: "llama3"
      api_key: "ollama"
      base_url: "http://localhost:11434/v1"
      batch_size: 10
```

## Usage examples

Basic usage — parse a raw log and read the inferred template:

```python
from detectmatelibrary.parsers.logbatcher import LogBatcherParser, LogBatcherParserConfig
import detectmatelibrary.schemas as schemas

config = LogBatcherParserConfig(
    api_key="<YOUR_API_KEY>",
    model="gpt-4o-mini",
    batch_size=10,
)

parser = LogBatcherParser(name="LogBatcherParser", config=config)

input_log = schemas.LogSchema({
    "logID": "1",
    "log": "User admin logged in from 192.168.1.10",
})

output = schemas.ParserSchema()
parser.parse(input_log, output)

print(output["template"])    # e.g. "User <*> logged in from <*>"
print(output["variables"])   # e.g. ["admin", "192.168.1.10"]
print(output["EventID"])     # integer index assigned by the cache
```

Using a local Ollama instance:

```python
config = LogBatcherParserConfig(
    api_key="ollama",
    model="llama3",
    base_url="http://localhost:11434/v1",
    batch_size=10,
)
parser = LogBatcherParser(name="LogBatcherParser", config=config)
```

Passing config as a dict:

```python
parser = LogBatcherParser(config={
    "method_type": "logbatcher_parser",
    "api_key": "<YOUR_API_KEY>",
    "model": "gpt-4o-mini",
    "batch_size": 10,
})
```

Go back to [Index](../index.md)
