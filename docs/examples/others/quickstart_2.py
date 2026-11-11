# flake8: noqa

PATH = "tests/test_data/"

# --8<-- [start:prepare]
from detectmatelibrary.helper.from_to import From


# Define your PATH to get the data
template_path = f"{PATH}audit_templates.txt"
log_path = f"{PATH}audit.log"
apache_path = f"{PATH}apache.log"

all_logs = []
for apache_log in From.log(None, apache_path, do_process=False):
    apache_log["logID"] = "Apache_" + apache_log["logID"]
    apache_log["logSource"] = "Apache_logs"
    all_logs.append(apache_log)

for audit_log in From.log(None, log_path, do_process=False):
    audit_log["logID"] = "Audit_" + audit_log["logID"]
    audit_log["logSource"] = "Audit_logs"
    all_logs.append(audit_log)

# --8<-- [end:prepare]

import redis

client = redis.Redis(host='localhost', port=6379, decode_responses=True)
client.flushdb()
client.close()

# --8<-- [start:initialize]

from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig
from detectmatelibrary.parsers.autoparser import AutoParserConfig

from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig

from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegationConfig

from detectmatelibrary.pipeline import PipelineConfig, Pipeline


config = PipelineConfig(
    do_parsing=True,
    do_aggregation=True,
    n_workers=1,
    parsers=[
        TemplateCppTreeMatcherConfig(
            path_templates=template_path,
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
        NewValueDetectorConfig(
            data_use_configure=1000,
            data_use_training=1,
            auto_config=True,
            parser="TreeMatcher_from_Audit_logs",
            connector_name="Redis",
            connector_url="http://localhost:6379:0",
        ),
        CharsetDetectorConfig(
            data_use_configure=1000,
            data_use_training=1,
            auto_config=True,
            parser="TreeMatcher_from_Audit_logs",
            connector_name="Redis",
            connector_url="http://localhost:6379:0",
        ),
        NewValueDetectorConfig(
            data_use_configure=100,
            data_use_training=1,
            auto_config=True,
            parser="AutoParser_from_Apache_logs",
            connector_name="Redis",
            connector_url="http://localhost:6379:1",
        ),
        CharsetDetectorConfig(
            data_use_configure=500,
            data_use_training=1,
            auto_config=True,
            parser="AutoParser_from_Apache_logs",
            connector_name="Redis",
            connector_url="http://localhost:6379:1",
        ),
    ],
    aggregator=LogIDCountAggegationConfig(
        max_count=2,
        connector_name="Redis",
        connector_url="http://localhost:6379:2",
    )
)

pipeline = Pipeline(config=config)

# --8<-- [end:initialize]

# --8<-- [start:run]

from tqdm import tqdm

for log in tqdm(all_logs):
    pipeline.process(log)

# --8<-- [end:run]

# --8<-- [start:get_data]

import detectmatelibrary.schemas as sc

# Get an alert from Audit
sc.set_connector(connector="Redis", url="http://localhost:6379:0")
print(sc.DetectorSchema.from_id("CharsetDetector_from_TreeMatcher_from_Audit_logs_15"))

# Get an alert from Apache
sc.set_connector(connector="Redis", url="http://localhost:6379:1")
print(sc.DetectorSchema.from_id(
    "NewValueDetector_from_AutoParser_from_Apache_logs_377"
))

# Get an aggreate alert
sc.set_connector(connector="Redis", url="http://localhost:6379:2")
print(sc.AggregateSchema.from_id("LogIDCountAggregator_15"))

# --8<-- [end:get_data]
