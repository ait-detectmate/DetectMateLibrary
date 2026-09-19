from detectmatelibrary.detectors.random_detector import RandomDetectorConfig
from detectmatelibrary.detectors.bigram_frequency_detector import (
    BigramFrequencyDetectorConfig,
)
from detectmatelibrary.detectors.charset_detector import CharsetDetectorConfig
from detectmatelibrary.detectors.new_value_combo_detector import (
    NewValueComboDetectorConfig,
)
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetectorConfig
from detectmatelibrary.detectors.ecvc_detector import ECVCDetectorConfig
from detectmatelibrary.detectors.event_sequence_detector import (
    EventSequenceDetectorConfig,
)
from detectmatelibrary.detectors.logbert_detector import LogBertDetectorConfig
from detectmatelibrary.detectors.new_event_detector import NewEventDetectorConfig
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetectorConfig
from detectmatelibrary.detectors.scvs_detector import SCVSDetectorConfig
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetectorConfig

from detectmatelibrary.common.core import CoreConfig
from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.variable_detector import VariableDetectorConfig
from detectmatelibrary.common.deeplearning_detector import DeepLearningDetectorConfig

import yaml


# %% Methods
def append_docs(docs: str, start_cmd: str, end_cmd: str, add: str) -> None:
    start_idx = docs.index(start_cmd)
    end_idx = docs.index(end_cmd)
    if start_idx > end_idx:
        raise Exception(f"'{start_cmd}' should be before '{end_cmd}'")

    return docs[: start_idx + 1] + [add] + docs[end_idx:]


def get_arguments(
    config: CoreConfig, exclude_inherited_from: type[CoreConfig] | None = None
) -> str:
    arguments = (
        "| Field  | Type  | Default Value| Description|\n|-------|------|-----|---|\n"
    )
    for arg in config.get_docs(exclude_inherited_from=exclude_inherited_from):
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


def update_docs(
    config: CoreConfig,
    doc_path: str,
    exclude_inherited_from: type[CoreConfig] | None = None,
) -> None:
    try:
        with open(doc_path, "r") as f:
            docs = f.readlines()

        # The "Configuration arguments" table only shows what this detector
        # adds itself -- parameters shared with other detectors are
        # documented once in docs/detectors.md (see update_shared_docs below)
        # rather than repeated on every detector page.
        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start arguments -->\n",
            end_cmd="<!-- End arguments -->\n",
            add=get_arguments(config, exclude_inherited_from=exclude_inherited_from),
        )

        # The YAML example stays complete (every field, not just this
        # detector's own ones) -- it's meant to be copy-pasted as a working
        # config, so it can't skip fields just because they're documented
        # elsewhere.
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


def update_shared_docs(doc_path: str) -> None:
    """Fill docs/detectors.md's tables of parameters shared across several
    detectors: fields every detector has (CoreDetectorConfig), plus the two
    families that add their own shared block on top (VariableDetectorConfig,
    DeepLearningDetectorConfig)."""
    try:
        with open(doc_path, "r") as f:
            docs = f.readlines()

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start common_arguments -->\n",
            end_cmd="<!-- End common_arguments -->\n",
            add=get_arguments(CoreDetectorConfig()),
        )
        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start variable_arguments -->\n",
            end_cmd="<!-- End variable_arguments -->\n",
            add=get_arguments(
                VariableDetectorConfig(), exclude_inherited_from=CoreDetectorConfig
            ),
        )
        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start deeplearning_arguments -->\n",
            end_cmd="<!-- End deeplearning_arguments -->\n",
            add=get_arguments(
                DeepLearningDetectorConfig(), exclude_inherited_from=CoreDetectorConfig
            ),
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
#
# Each entry's second element is the immediate base class whose fields that
# detector's table should leave out -- CoreDetectorConfig for detectors with
# no family in between, or VariableDetectorConfig/DeepLearningDetectorConfig
# for the two families that add their own shared block on top. Either way,
# the excluded fields are already documented once in docs/detectors.md by
# update_shared_docs.
DETECTOR_DOCS: list[tuple[CoreConfig, type[CoreConfig], str]] = [
    (RandomDetectorConfig(), CoreDetectorConfig, "docs/detectors/random_detector.md"),
    (
        BigramFrequencyDetectorConfig(),
        VariableDetectorConfig,
        "docs/detectors/bigram_frequency.md",
    ),
    (CharsetDetectorConfig(), VariableDetectorConfig, "docs/detectors/charset.md"),
    (
        NewValueComboDetectorConfig(),
        VariableDetectorConfig,
        "docs/detectors/combo.md",
    ),
    (DeeplogDetectorConfig(), DeepLearningDetectorConfig, "docs/detectors/deeplog.md"),
    (ECVCDetectorConfig(), CoreDetectorConfig, "docs/detectors/ecvc_detector.md"),
    (
        EventSequenceDetectorConfig(),
        CoreDetectorConfig,
        "docs/detectors/event_sequence.md",
    ),
    (LogBertDetectorConfig(), DeepLearningDetectorConfig, "docs/detectors/logbert.md"),
    (NewEventDetectorConfig(), CoreDetectorConfig, "docs/detectors/new_event.md"),
    (NewValueDetectorConfig(), VariableDetectorConfig, "docs/detectors/new_value.md"),
    (RuleDetectorConfig(), CoreDetectorConfig, "docs/detectors/rule_based.md"),
    (SCVSDetectorConfig(), CoreDetectorConfig, "docs/detectors/scvs_detector.md"),
    (
        ValueRangeDetectorConfig(),
        VariableDetectorConfig,
        "docs/detectors/value_range.md",
    ),
]

update_shared_docs("docs/detectors.md")

for detector_config, exclude_base, doc_path in DETECTOR_DOCS:
    update_docs(detector_config, doc_path=doc_path, exclude_inherited_from=exclude_base)
