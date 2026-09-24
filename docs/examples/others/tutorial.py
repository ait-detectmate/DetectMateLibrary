# --8<-- [start:read]
from pathlib import Path
from detectmatelibrary.helper.from_to import From

try:
    ROOT = Path(__file__).resolve().parents[3]
except NameError:  # running inside a Jupyter notebook
    ROOT = Path.cwd().resolve().parents[1]

log_path = str(ROOT / "tests" / "test_data" / "logs.log")

# do_process=False turns From.log into a pure reader: it yields raw
# LogSchema objects without running them through a parser yet, so the
# `component` argument (normally a parser) is never touched and can be
# left as None. That's all we need to look at the data before deciding
# how to parse it.
raw_logs = list(From.log(None, log_path, do_process=False))
print(f"read {len(raw_logs)} raw log lines")
print(raw_logs[0]["log"])
# --8<-- [end:read]

# --8<-- [start:own_parser]
from detectmatelibrary.parsers.template_matcher import MatcherParser  # noqa: E402

templates_path = str(ROOT / "tests" / "test_data" / "logs_templates.txt")

config_dict = {
    "parsers": {
        "MatcherParser": {
            "auto_config": True,
            "method_type": "matcher_parser",
            "path_templates": templates_path,
            "log_format": "type=<Type> msg=audit(<Time>:<Serial>): <Content>",
        }
    }
}
parser = MatcherParser(name="MatcherParser", config=config_dict)

parsed_logs = [parser.process(raw) for raw in raw_logs]
for plog in parsed_logs:
    print(plog["EventID"], plog["template"])
# --8<-- [end:own_parser]

# --8<-- [start:detectors]
from detectmatelibrary.detectors.new_value_detector import NewValueDetector  # noqa: E402
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetector  # noqa: E402

# NewValueDetector watches two fields we picked while writing the templates
# above: the key=value pair inside CONFIG_CHANGE (EventID 1, position 0) and
# the process name inside SYSCALL (EventID 2, position 22, see the "comm="
# slot in the third template line).
new_value_detector = NewValueDetector(
    name="NewValueDetector",
    config={
        "detectors": {
            "NewValueDetector": {
                "method_type": "new_value_detector",
                "auto_config": False,
                # Train on the first 3 logs (one DAEMON_START, one
                # CONFIG_CHANGE, one SYSCALL), then detect on the rest.
                "data_use_training": 3,
                "params": {},
                "events": {
                    1: {"op_change": {"variables": [{"pos": 0, "name": "op_value"}]}},
                    2: {"proc": {"variables": [{"pos": 22, "name": "comm"}]}},
                },
            }
        }
    },
)

# EventSequenceDetector instead watches the *order* of EventIDs, independent
# of what's inside each log. A window of 2 means it remembers which
# consecutive event-ID pairs occurred during training.
event_sequence_detector = EventSequenceDetector(
    name="EventSequenceDetector",
    config={
        "detectors": {
            "EventSequenceDetector": {
                "method_type": "event_sequence_detector",
                "auto_config": False,
                "data_use_training": 3,
                "params": {"fixed_window_size": 2},
            }
        }
    },
)

alerts = []
print(f"{'#':>2}  {'EventID':>7}  {'NewValue':>8}  {'EventSequence':>13}")
for i, plog in enumerate(parsed_logs, start=1):
    nv_alert = new_value_detector.process(plog)
    es_alert = event_sequence_detector.process(plog)
    print(
        f"{i:>2}  {plog['EventID']:>7}  {str(bool(nv_alert)):>8}  {str(bool(es_alert)):>13}"
    )
    if nv_alert:
        alerts.append(nv_alert)
    if es_alert:
        alerts.append(es_alert)
# --8<-- [end:detectors]

# --8<-- [start:aggregate]
from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregation  # noqa: E402

aggregator = BasicConcatAggregation(
    name="BasicConcatAggregator",
    config={
        "alert_aggregators": {
            "BasicConcatAggregator": {
                "method_type": "basic_concat_aggregator",
                "buffer_size": 2,
                "auto_config": False,
            }
        }
    },
)

for alert in alerts:
    aggregated = aggregator.process(alert)
    if aggregated:
        print(aggregated["detectorIDs"], aggregated["logIDs"])
# --8<-- [end:aggregate]
