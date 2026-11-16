# flake8: noqa

PATH = "tests/test_data/"

# --8<-- [start:config]
# Define your PATH to get the data
template_path = f"{PATH}audit_templates.txt"
log_path = f"{PATH}audit.log"


config_dict = {
    "parsers": {
        "TreeMatcher": {
            "method_type": "tree_matcher",
            "params": {
                "path_templates": template_path,
                "log_format": "type=<Type> msg=audit(<Time>): <Content>",
            }

        }
    },
    "detectors": {
        "NewValueDetector": {
            "method_type": "new_value_detector",
            "auto_config": True,
            "params": {
                "data_use_configure": 1000,
                "data_use_training": 1,
            }
        },
        "CharsetDetector": {
            "method_type": "charset_detector",
            "auto_config": True,
            "params": {
                "data_use_configure": 1000,
                "data_use_training": 1,
            }
        }
    },
    "alert_aggregators": {
        "TimeDeltaAggregator": {
            "method_type": "time_delta_aggregator",
            "delta": 4.0,
        }
    }
}
# --8<-- [end:config]

# --8<-- [start:other]
from detectmatelibrary.helper.from_to import From

print_one = True  # just print one time the output

for log in From.log(None, log_path, do_process=False):
    print(log)
    break  # Remove the break to see more raw logs
# --8<-- [end:other]


# --8<-- [start:parse]
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcher


print(parser := TemplateCppTreeMatcher(name="TreeMatcher", config=config_dict))

parsed_logs = []
print_one = True  # just print one time the output

for parsed_log in From.log(parser, log_path):
    if print_one:
        print(parsed_log)
        print_one = False

    parsed_logs.append(parsed_log)
# --8<-- [end:parse]

# --8<-- [start:detectors]
from detectmatelibrary.detectors.charset_detector import CharsetDetector
from detectmatelibrary.detectors.new_value_detector import NewValueDetector


print(detector1 := CharsetDetector(name="CharsetDetector", config=config_dict))
print(detector2 := NewValueDetector(name="NewValueDetector", config=config_dict))

alert_logs = []
print_one = True  # just print one time the output

for parsed_log in parsed_logs:

    if (alert1 := detector1.process(parsed_log)) is not None:
        alert_logs.append(alert1)

    if (alert2 := detector2.process(parsed_log)) is not None:
        alert_logs.append(alert2)

        if print_one:
            print(alert2)
            print_one = False

# --8<-- [end:detectors]

# --8<-- [start:aggregator]
from detectmatelibrary.alert_aggregation.time_delta import TimeDeltaAggregation

print(
    agg := TimeDeltaAggregation(name="TimeDeltaAggregator", config=config_dict)
)

print_one = True  # just print one time the output

for alert in alert_logs:
    if (agg_alert := agg.process(alert)) is not None:
        if print_one:
            print(agg_alert)
            print_one = False

# --8<-- [end:aggregator]

# --8<-- [start:pipeline]
from detectmatelibrary.pipeline import PipelineConfig, Pipeline

config = PipelineConfig(
        do_parsing=True,  # Use the parser
        do_aggregation=True,  # Use the aggregator
        parsers=[{
            "parsers": {
                "TreeMatcher": {
                    "method_type": "tree_matcher",
                    "params": {
                        "path_templates": template_path,
                        "log_format": "type=<Type> msg=audit(<Time>): <Content>",
                    }
                }
            }
        }],
        n_workers=1,  # You can add parallelization for the detectors
        detectors=[
            {
                "detectors": {
                    "NewValueDetector": {
                        "method_type": "new_value_detector",
                        "auto_config": True,
                        "params": {
                            "data_use_configure": 1000,
                            "data_use_training": 1,
                        }
                    }
                },
            },
           {
                "detectors": {
                    "CharsetDetector": {
                        "method_type": "charset_detector",
                        "auto_config": True,
                        "params": {
                            "data_use_configure": 1000,
                            "data_use_training": 1,
                        }
                    },
                },
           }
        ],
        aggregator={
            "alert_aggregators": {
                "TimeDeltaAggregator": {
                    "method_type": "time_delta_aggregator",
                    "delta": 4.0,
                }
            }
        }
    )

pipeline = Pipeline(config=config)

# --8<-- [end:pipeline]

# --8<-- [start:pipeline_run]
print_one = True  # just print one time the output

for agg_alert in From.log(pipeline, log_path):
    if agg_alert is not None and print_one:
        print(agg_alert)
        print_one = False

# --8<-- [end:pipeline_run]
