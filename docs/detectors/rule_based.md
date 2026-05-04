# Rule-based Detector

The Rule-based Detector raises alerts based on a configurable set of rules.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

The detector analyzes parsed logs one by one and checks which rules are triggered. When alerts are produced, the triggered rules and their messages are recorded in the `alertsObtain` field of the output schema. The `score` field contains the number of rules that triggered.

### Available rules

| Rule name | Description | Requires arguments | Enabled by default |
|---|---|---:|:---:|
| **R001 - TemplateNotFound** | Check whether the parser assigned a template to the log | No | Yes |
| **R002 - SpecificKeyword** | Check for one or more user-specified keywords in the log content | list of words | No |
| **R003 - CheckForExceptions** | Check for words commonly associated with exceptions or failures | No | Yes |
| **R004 - ErrorLevelFound** | If a Level field exists, check whether it indicates an error level | No | Yes |

Notes on table columns:

- **Rule name**: Identifier used in configuration.
- **Description**: What the rule checks.
- **Requires arguments**: Whether the rule needs additional arguments.
- **Enabled by default**: Whether the rule is active when not explicitly overridden.

## Configuration example

```yaml
detectors:
  RuleDetector:
    method_type: rule_detector
    auto_config: False
    params:
      rules:
        - rule: "R001 - TemplateNotFound"
        - rule: "R002 - SpecificKeyword"
          args:
            - "critical"
            - "anomaly"
```

## Example usage

```python
import detectmatelibrary.detectors.rule_detector as rd
from detectmatelibrary import schemas

rule_detector = rd.RuleDetector()

parser_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["var1"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})

alert = rule_detector.process(parser_data)
```

Go back [Index](../index.md)
