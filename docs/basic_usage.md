
# Getting started:  Basic usage

In this section, we will show different examples of the basic usage of the DetectMate Library.

## Parser

In this example, we will use the [`MatcherParser`](parsers/template_matcher.md) to parse audit data from the [AIT Log Data Set V2.0](https://zenodo.org/records/5789064). The code loads the logs, parse them and save the input and output in json files using [`from_to`](helper/from_to.md) module.

```python
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From, To


config_dict = {
    "parsers": {
        "MatcherParser": {
            "auto_config": True,
            "method_type": "matcher_parser",
            "path_templates": "ait_audit.txt",
            "log_format": r'type=<Type> msg=audit\(<Time>:<Serial>\): <Content>'
        }
    }
}
parser = MatcherParser(name="MatcherParser", config=config_dict)


for i, log in enumerate(From.log(parser, "audit.log", do_process=False)):
    To.json(log, "logs.json")

    parsed_log = parser.process(log)
    To.json(parsed_log, "parsed_log.json")

```

The logs will be save in `logs.json` in this format:

```json
{
"0": {
        "log": "type=USER_ACCT msg=audit(1642723741.072:375): pid=10125 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\" exe=\"/usr/sbin/cron\" hostname=? addr=? terminal=cron res=success'",
        "__version__": "1.0.0",
        "hostname": "",
        "logSource": "",
        "logID": "0"
    },
...
}
```
And the `parsed_log.json`:

```json
{
    "0": {
        "parserID": "MatcherParser",
        "parsedLogID": "10",
        "logID": "0",
        "parsedTimestamp": 1772027171,
        "logFormatVariables": {
            "Type": "USER_ACCT",
            "Serial": "375",
            "Time": "1642723741.072",
            "Content": "pid=10125 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\" exe=\"/usr/sbin/cron\" hostname=? addr=? terminal=cron res=success'"
        },
        "__version__": "1.0.0",
        "receivedTimestamp": 1772027171,
        "variables": [
            "10125",
            "0",
            "4294967295",
            "4294967295",
            "PAM:accounting",
            "\"root\"",
            "\"/usr/sbin/cron\"",
            "?",
            "?",
            "cron",
            "success"
        ],
        "log": "type=USER_ACCT msg=audit(1642723741.072:375): pid=10125 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\" exe=\"/usr/sbin/cron\" hostname=? addr=? terminal=cron res=success'",
        "parserType": "matcher_parser",
        "EventID": 0,
        "template": "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=<*> acct=<*> exe=<*> hostname=<*> addr=<*> terminal=<*> res=<*>'"
    },
...
}
```

## Detector

In this example, we will use the [`RandomDetector`](detectors/random_detector.md) with the parsed logs from the previous example.

```python
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From, To, FromTo

config_dict = {
    "detectors": {
        "RandomDetector": {
            "auto_config": False,
            "method_type": "random_detector",
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 0,
                            "name": "process",
                            "params": {
                                "threshold": 0.
                            }
                        }]
                    }
                }
            }
        }
    }
}
detector =  RandomDetector(name="RandomDetector", config=config_dict)

for alert in FromTo.json2json(detector, "parsed_log.json", "alerts.json"):
    if alert is not None:
        print("Anomaly detected!")
```

The alerts will be saved in `alerts.json` in this format:

```json
{
    "0": {
        "extractedTimestamps": [
            1642723752
        ],
        "receivedTimestamp": 1772032073,
        "score": 1.0,
        "detectionTimestamp": 1772032073,
        "alertID": "10",
        "detectorType": "random_detector",
        "detectorID": "RandomDetector",
        "description": "",
        "__version__": "1.0.0",
        "logIDs": [
            "6"
        ],
        "alertsObtain": {
            "process": "1.0"
        }
    },
...
}
```


Go back to [Index](index.md), to previous step: [Installation](installation.md) or to next step: [Create new component](create_components.md).
