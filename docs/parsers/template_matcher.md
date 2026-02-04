# Template matcher

Parser that take a set of templates an match them to a sequence of logs.

|            | Schema                 | Description        |
|------------|------------------------|--------------------|
| **Input**  | [LogSchema](../schemas.md)| Unstructured log   |
| **Output** | [ParserSchema](../schemas.md)| Structured log  |


## Configuration file

Example of a configuration file:

```yaml
parsers:
    MatcherParser:
        method_type: matcher_parser
        auto_config: False
        log_format: "type=<Type> msg=audit(<Time>): <Content>"
        time_format: null
        params:
            remove_spaces: True
            remove_punctuation: True
            lowercase: True
            path_templates: tests/test_folder/audit_templates.txt
```

## Example

Code examples of normal use cases of the parser:

```python
from detectmatelibrary.parsers.template_matcher import MatcherParser

from detectmatelibrary import schemas


config_dict = {
    "parsers": {
        "MatcherParser": {
            "auto_config": True,
            "method_type": "matcher_parser",
            "path_templates": "tests/test_folder/test_templates.txt"
        }
    }
}

test_template = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>"
test_log_match = 'pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting acct="root"'

parser = MatcherParser(name="MatcherParser", config=config_dict)
input_log = schemas.LogSchema({"log": test_log_match})
parser.process(input_log)

print(output_data.template == test_template)  # True
```
Go back [Index](../index.md)
