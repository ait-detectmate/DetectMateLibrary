# flake8: noqa

# --8<-- [start:example_1]
from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig

from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig

from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig

from detectmatelibrary.pipeline import PipelineConfig, Pipeline
import detectmatelibrary.schemas as schemas

config = PipelineConfig(
        do_parsing=True,  # Use the parser
        do_aggregation=True,  # Use the aggregator
        parsers=[TemplateCppTreeMatcherConfig(
            path_templates="docs/examples/data/tutorial_templates.txt",
            log_format="type=<Type> msg=audit(<Time>): <Content>"
        )],
        n_workers=1,  # You can add parallelization for the detectors
        detectors=[
            {
                "detectors": {
                    "ECVCDetector": {
                        "method_type": "ecvc_detector",
                        "data_use_configure": 100,
                        "window_size": 10,
                        "seed": 0,
                        "validation_per": 0.,
                        "threshold_method": "mean"
                    }
                }
            },
            CharsetDetectorConfig(
                data_use_configure=100,
                data_use_training=1,
                auto_config=True,
            )
        ],
        aggregator=LogIDCountAggegationConfig(max_count=1)
    )

pipeline = Pipeline(config=config)
pipeline.process(schemas.LogSchema({
    "logID": "0",
    "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'",
}))
# --8<-- [end:example_1]

# --8<-- [start:example_2]
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig
from detectmatelibrary.parsers.autoparser import AutoParserConfig

from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig

from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig

from detectmatelibrary.pipeline import PipelineConfig, Pipeline
import detectmatelibrary.schemas as schemas


config = PipelineConfig(
    do_parsing=True,
    do_aggregation=True,
    n_workers=1,
    parsers=[
        TemplateCppTreeMatcherConfig(
            path_templates="docs/examples/data/tutorial_templates.txt",
            log_format="type=<Type> msg=audit(<Time>): <Content>",
            log_source="Audit_logs",
        ),
        AutoParserConfig(
            fix_type="Apache",
            log_source="Apache_logs",
            data_use_training=1,
        ),
    ],
    detectors=[
        CharsetDetectorConfig(
            data_use_configure=1000,
            data_use_training=1,
            auto_config=True,
            parser="TreeMatcher_from_Audit_logs"
        ),
        CharsetDetectorConfig(
            data_use_configure=10,
            data_use_training=1,
            auto_config=True,
            parser="AutoParser_from_Apache_logs",
        )
    ],
    aggregator=LogIDCountAggegationConfig(max_count=1)
)
pipeline = Pipeline(config=config)

pipeline.process(schemas.LogSchema({
    "logID": "0",
    "log": "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\"'",
    "logSource": "Audit_logs"
}))

# --8<-- [end:example_2]
