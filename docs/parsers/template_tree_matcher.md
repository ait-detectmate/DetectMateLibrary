# Template Tree Matcher

The Template Tree Matcher is a parser that matches incoming logs against a set of templates using a tree-based depth-first search. It provides faster matching for batch workloads compared with the streaming Template Matcher.

This parser wraps functionality from the DetectMatePerformance project: https://github.com/ait-detectmate/DetectMatePerformance. Prefer  use the performance implementation when parsing many log lines in non-stream (batch) mode.

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

## Configuration

Typical TemplateTreeMatcher config options:

- `method_type` (string): parser type identifier (for example `"tree_matcher"`).
- `path_templates` (string or null): path to the newline-delimited template file. If `null`, the matcher runs without templates.
- `auto_config` (bool): whether to attempt an optional auto-configuration phase (not required).

Note: this matcher removes non-alphanumeric characters from logs and templates before matching, except for the `<*>` token. Ensure your templates are compatible with that normalization.

Example YAML fragment:
```yaml
parsers:
  TemplateTreeMatcher:
    method_type: tree_matcher
    auto_config: False
    params:
      path_templates: path/to/templates.txt
```

## Usage example

Simple usage — load templates and match a log:

```python
from detectmatelibrary.parsers.tree_matcher import TemplateTreeMatcher
from detectmatelibrary import schemas

# instantiate parser (config can be a dict or a config object)
cfg = {
    "parsers": {
        "TreeMatcher": {
            "method_type": "tree_matcher",
            "params": {
                "path_templates": "tests/test_folder/test_templates.txt"
            }
        }
    }
}

parser = TemplateTreeMatcher(name="TreeMatcher", config=cfg)

# match a log
input_log = schemas.LogSchema({
    "logID": "0",
    "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'"
})
parsed = parser.process(input_log)  # or call parser.parse / parser.match depending on the API

# parsed is a ParserSchema. Inspect fields:
print(parsed.template)   # matched template text
print(parsed.variables)  # list of extracted parameters
```

Go back to [Index](../index.md)
