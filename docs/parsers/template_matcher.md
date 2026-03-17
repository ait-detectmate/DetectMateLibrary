# Template matcher

Parser that takes a set of templates and matches them to incoming logs. It extracts parameters from positions marked with the <*> wildcard and returns a ParserSchema with the matched template and the extracted variables.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md) | Unstructured log   |
| **Output** | [ParserSchema](../schemas.md) | Structured log   |

## Overview

The template matcher is a lightweight, fast parser intended for logs that follow stable textual templates with variable fields. Templates use the token `<*>` to mark wildcard slots. The matcher:

- Preprocesses logs and templates (remove spaces, punctuation, lowercase) based on config.
- Finds the first template that matches and extracts all wildcard parameters in order.
- Populates ParserSchema fields: `EventID`, `template`, `variables`,  `logID`, and related fields.

This parser is deterministic and designed for high-throughput use when templates are known in advance.

## Template format

- Templates are plain text lines in a template file.
- Use `<*>` for wildcard slots.

Example template file (templates.txt):
```text
pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>
login success: user=<*> source=<*>
```

## Configuration

Typical MatcherParser config options (fields in config class):

- `method_type`: must match the parser type ("matcher_parser" or configured name).
- `path_templates`: path to the newline-delimited template file.
- `remove_spaces` (bool, default True): remove all spaces during matching.
- `remove_punctuation` (bool, default True): strip punctuation except the `<*>` token.
- `lowercase` (bool, default True): lowercase logs and templates before matching.
- `auto_config` (bool): whether to attempt any auto-configuration phase (not required).

Example YAML entry:
```yaml
parsers:
  MatcherParser:
    method_type: matcher_parser
    auto_config: False
    params:
      remove_spaces: True
      remove_punctuation: True
      lowercase: True
      path_templates: path/to/templates.txt
```

## Usage examples

Simple usage — load templates and match a log:

```python
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary import schemas

# instantiate parser (config can be a dict or config object)
cfg = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "params": {
                "path_templates": "tests/test_folder/test_templates.txt",
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True
            }
        }
    }
}

parser = MatcherParser(name="MatcherParser", config=cfg)

# match a log
input_log = schemas.LogSchema({"logID": "0", "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'"})
parsed = parser.process(input_log)  # or parser.parse / parser.match depending on wrapper API

# parsed is a ParserSchema (or an output container). Check fields:
print(parsed.template)         # matched template text
print(parsed.variables)        # list of extracted params
```


Go back to [Index](../index.md)
