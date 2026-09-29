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
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetectorConfig
from detectmatelibrary.detectors.logbert_detector import LogBertDetectorConfig
from detectmatelibrary.detectors.new_event_detector import NewEventDetectorConfig
from detectmatelibrary.detectors.new_value_detector import NewValueDetectorConfig
from detectmatelibrary.detectors.rule_detector import RuleDetectorConfig
from detectmatelibrary.detectors.scvs_detector import SCVSDetectorConfig
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetectorConfig

from detectmatelibrary.parsers.autoparser import AutoParserConfig
from detectmatelibrary.parsers.drain import DrainConfig
from detectmatelibrary.parsers.json_parser import JsonParserConfig
from detectmatelibrary.parsers.logbatcher import LogBatcherParserConfig
from detectmatelibrary.parsers.template_matcher import MatcherParserConfig
from detectmatelibrary.parsers.tree_matcher import TemplateCppTreeMatcherConfig

from detectmatelibrary.common.core import CoreConfig
from detectmatelibrary.common.detector import CoreDetectorConfig
from detectmatelibrary.common.parser import CoreParserConfig
from detectmatelibrary.common.variable_detector import VariableDetectorConfig
from detectmatelibrary.common.deeplearning_detector import DeepLearningDetectorConfig

from typing import Any


# %% Methods
def append_docs(docs: list[str], start_cmd: str, end_cmd: str, add: str) -> list[str]:
    start_idx = docs.index(start_cmd)
    end_idx = docs.index(end_cmd)
    if start_idx > end_idx:
        raise Exception(f"'{start_cmd}' should be before '{end_cmd}'")

    return docs[: start_idx + 1] + [add] + docs[end_idx:]


# One collapsible table per YAML block, in the order the blocks appear in the
# config (rendered with material's admonition + pymdownx.details).
BLOCKS = [
    ("top", "Top level"),
    ("params", "params"),
    ("auto_config_params", "auto_config_params (read only while auto_config is true)"),
]


def _cell(value: Any) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def get_arguments(rows: list[dict[str, Any]], with_scope: bool = True) -> str:
    """Render get_docs() rows as one collapsible markdown table per YAML block.

    A block holding any specific field starts open, a block of only
    shared fields starts collapsed. auto_config_params always starts
    collapsed: its defaults rarely need changing. Within a block, specific
    fields come first.
    """
    header = ["Field", "Type", "Default", "Scope", "Description"]
    if not with_scope:
        header.remove("Scope")

    tables = []
    for block, title in BLOCKS:
        block_rows = sorted(
            (r for r in rows if r["Block"] == block), key=lambda r: r["Scope"] != "specific"
        )
        if not block_rows:
            continue
        is_open = block != "auto_config_params" and any(r["Scope"] == "specific" for r in block_rows)
        lines = [
            f'???{"+" if is_open else ""} note "{title}"',
            "",
            "    | " + " | ".join(header) + " |",
            "    |" + "---|" * len(header),
        ]
        for r in block_rows:
            default = _cell(r["Default value"])
            if r["Default changed"]:
                default += f" (shared: {_cell(r['Shared default'])})"
            cells = [f"`{r['Name']}`", _cell(r["Type"]), default, r["Scope"], _cell(r["Description"])]
            if not with_scope:
                cells.remove(r["Scope"])
            lines.append("    | " + " | ".join(cells) + " |")
        tables.append("\n".join(lines) + "\n")
    return "\n".join(tables)


def update_docs(
    config: CoreConfig,
    doc_path: str,
    shared_base: type[CoreConfig],
) -> None:
    try:
        with open(doc_path, "r") as f:
            docs = f.readlines()

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start arguments -->\n",
            end_cmd="<!-- End arguments -->\n",
            add=get_arguments(config.get_docs(shared_base=shared_base)),
        )

        with open(doc_path, "w") as f:
            f.writelines(docs)
    except Exception as e:
        raise Exception(f"While updating {doc_path} -> {str(e)}")


def _family_rows(config: CoreConfig) -> list[dict[str, Any]]:
    """What a detector family adds on top of the fields every detector has."""
    return [r for r in config.get_docs(shared_base=CoreDetectorConfig) if r["Scope"] == "specific"]


def update_shared_args_detectors(doc_path: str) -> None:
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
            add=get_arguments(CoreDetectorConfig().get_docs(), with_scope=False),
        )
        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start variable_arguments -->\n",
            end_cmd="<!-- End variable_arguments -->\n",
            add=get_arguments(_family_rows(VariableDetectorConfig()), with_scope=False),
        )
        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start deeplearning_arguments -->\n",
            end_cmd="<!-- End deeplearning_arguments -->\n",
            add=get_arguments(_family_rows(DeepLearningDetectorConfig()), with_scope=False),
        )

        with open(doc_path, "w") as f:
            f.writelines(docs)
    except Exception as e:
        raise Exception(f"While updating {doc_path} -> {str(e)}")


def update_shared_args_parsers(doc_path: str) -> None:
    """Fill docs/parsers.md's tables of parameters shared across several
    parsers: fields every parser has (CoreParserConfig)."""
    try:
        with open(doc_path, "r") as f:
            docs = f.readlines()

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start common_arguments -->\n",
            end_cmd="<!-- End common_arguments -->\n",
            add=get_arguments(CoreParserConfig().get_docs(), with_scope=False),
        )
        with open(doc_path, "w") as f:
            f.writelines(docs)
    except Exception as e:
        raise Exception(f"While updating {doc_path} -> {str(e)}")


# %% Documentation update
#
# Every config below drives its own doc page: whenever a Field is added,
# removed or its description/default changes, re-running this script (or
# `pytest`, which executes it as a doc example) regenerates the
# "Configuration arguments" tables in the corresponding page, so the docs
# never drift from the code. The YAML example on each page is hand-written
# (docs/examples/<type>/<name>.yaml) and kept valid by its Python example,
# which loads it and runs as a test.
#
# Each entry's second element is the family base the page is documented
# against: a field that also exists there is marked `shared`, everything else
# `specific`. CoreDetectorConfig for detectors with no family in between,
# VariableDetectorConfig/DeepLearningDetectorConfig for the two families.
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

PARSER_DOCS: list[tuple[CoreConfig, type[CoreConfig], str]] = [
    (AutoParserConfig(), CoreParserConfig, "docs/parsers/auto_parser.md"),
    (DrainConfig(), CoreParserConfig, "docs/parsers/drain_parser.md"),
    (JsonParserConfig(), CoreParserConfig, "docs/parsers/json_parser.md"),
    (LogBatcherParserConfig(), CoreParserConfig, "docs/parsers/logbatcher_parser.md"),
    (MatcherParserConfig(), CoreParserConfig, "docs/parsers/template_matcher.md"),
    (
        TemplateCppTreeMatcherConfig(),
        CoreParserConfig,
        "docs/parsers/template_tree_matcher.md",
    ),
]

update_shared_args_detectors("docs/detectors.md")
update_shared_args_parsers("docs/parsers.md")

for detector_config, shared_base, doc_path in DETECTOR_DOCS:
    update_docs(detector_config, doc_path=doc_path, shared_base=shared_base)

for parser_config, shared_base, doc_path in PARSER_DOCS:
    update_docs(parser_config, doc_path=doc_path, shared_base=shared_base)
