from detectmatelibrary.detectors.random_detector import RandomDetectorConfig
from detectmatelibrary.detectors.bigram_frequency_detector import BigramFrequencyDetectorConfig
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetectorConfig
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetectorConfig
from detectmatelibrary.detectors.logbert_detector import LogBertDetectorConfig
from detectmatelibrary.detectors.new_event_detector import NewEventDetectorConfig
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetectorConfig
from detectmatelibrary.detectors.scvs_detector import SCVSDetectorConfig
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetectorConfig

from detectmatelibrary.common.core import CoreConfig

import yaml


# %% Methods
def append_docs(docs: str, start_cmd: str, end_cmd: str, add: str) -> None:
    start_idx = docs.index(start_cmd)
    end_idx = docs.index(end_cmd)
    if start_idx > end_idx:
        raise Exception(f"'{start_cmd}' should be before '{end_cmd}'")

    return docs[: start_idx + 1] + [add] + docs[end_idx:]


def get_arguments(config: CoreConfig) -> str:
    arguments = (
        "| Field  | Type  | Default Value| Description|\n|-------|------|-----|---|\n"
    )
    for arg in config.get_docs():
        arguments += f"|{arg['Name']}|{arg['Type']}|{arg['Default value']}|{arg['Description']}|\n"
    return arguments


def config_yaml(config: CoreConfig) -> str:
    pretty_yaml = yaml.dump(
        config.to_dict("<COMPONENT_NAME>"),
        indent=4,
        default_flow_style=False,
        sort_keys=False,
    )
    return "```yaml\n" + pretty_yaml + "```\n"


def update_docs(config: CoreConfig, doc_path: str) -> None:
    try:
        with open(doc_path, "r") as f:
            docs = f.readlines()

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start arguments -->\n",
            end_cmd="<!-- End arguments -->\n",
            add=get_arguments(config),
        )

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start config -->\n",
            end_cmd="<!-- End config -->\n",
            add=config_yaml(config),
        )

        with open(doc_path, "w") as f:
            f.writelines(docs)
    except Exception as e:
        raise Exception(f"While updating {doc_path} -> {str(e)}")


# %% Documentation update
#
# Every detector config below drives its own doc page: whenever a Field is
# added, removed or its description/default changes, re-running this script
# (or `pytest`, which executes it as a doc example) regenerates the
# "Configuration arguments" table and the "Start config"/"End config" YAML
# block in the corresponding page, so the docs never drift from the code.
DETECTOR_DOCS: list[tuple[CoreConfig, str]] = [
    (RandomDetectorConfig(), "docs/detectors/random_detector.md"),
    (BigramFrequencyDetectorConfig(), "docs/detectors/bigram_frequency.md"),
    (CharsetDetectorConfig(), "docs/detectors/charset.md"),
    (NewValueComboDetectorConfig(), "docs/detectors/combo.md"),
    (DeeplogDetectorConfig(), "docs/detectors/deeplog.md"),
    (ECVCDetectorConfig(), "docs/detectors/ecvc_detector.md"),
    (EventSequenceDetectorConfig(), "docs/detectors/event_sequence.md"),
    (LogBertDetectorConfig(), "docs/detectors/logbert.md"),
    (NewEventDetectorConfig(), "docs/detectors/new_event.md"),
    (NewValueDetectorConfig(), "docs/detectors/new_value.md"),
    (RuleDetectorConfig(), "docs/detectors/rule_based.md"),
    (SCVSDetectorConfig(), "docs/detectors/scvs_detector.md"),
    (ValueRangeDetectorConfig(), "docs/detectors/value_range.md"),
]

for detector_config, doc_path in DETECTOR_DOCS:
    update_docs(detector_config, doc_path=doc_path)
