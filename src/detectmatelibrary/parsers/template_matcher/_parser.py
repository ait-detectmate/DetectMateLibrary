from detectmatelibrary.parsers.template_matcher._matcher_op import TemplateMatcher, TemplateMetadata
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from typing import Any
import csv
import os
import re

_NAMED_WC_RE = re.compile(r'<([A-Za-z_]\w*)>')


class TemplatesNotFoundError(Exception):
    pass


class TemplateNoPermissionError(Exception):
    pass


def _compile_templates(
    raw_templates: list[str],
    event_id_labels: list[str | None] | None = None,
) -> tuple[list[str], dict[int, TemplateMetadata]]:
    """Convert named wildcards to <*> and record label order and event ID
    labels.

    Args:
        raw_templates: Raw template strings, possibly containing named wildcards.
        event_id_labels: Optional per-template event ID labels (from CSV EventId column).
                         If provided, must have the same length as raw_templates.

    Returns:
        compiled: Template strings with only <*> wildcards, ready for TemplatesManager.
        metadata: Mapping of template index to TemplateMetadata.

    Raises:
        ValueError: If a template mixes <*> and named wildcards.
    """
    compiled: list[str] = []
    metadata: dict[int, TemplateMetadata] = {}

    for i, raw in enumerate(raw_templates):
        has_anon = "<*>" in raw
        labels = _NAMED_WC_RE.findall(raw)
        has_named = bool(labels)

        if has_anon and has_named:
            raise ValueError(
                f"Template mixes <*> and named wildcards: {raw!r}. "
                "Use either <*> (positional) or <label> (named) exclusively."
            )

        compiled_tpl = _NAMED_WC_RE.sub("<*>", raw) if has_named else raw
        idx = len(compiled)
        compiled.append(compiled_tpl)
        eid_label = event_id_labels[i] if event_id_labels else None
        metadata[idx] = TemplateMetadata(event_id_label=eid_label, labels=labels)

    return compiled, metadata


def load_templates(path: str) -> tuple[list[str], list[str | None]]:
    """Load templates from a .txt or .csv file.

    Returns:
        A tuple of (template_strings, event_id_labels). For .txt files, all
        event_id_labels are None (positional IDs only). For .csv files, an
        optional EventId column provides named event ID labels.
    """
    if not os.path.exists(path):
        raise TemplatesNotFoundError(f"Templates file not found at: {path}")
    if not os.access(path, os.R_OK):
        raise TemplateNoPermissionError(
            f"You do not have the permission to access the templates file: {path}"
        )
    templates: list[str] = []
    eid_labels: list[str | None] = []
    if path.endswith(".txt"):
        with open(path, "r") as f:
            for line in f:
                s = line.strip()
                if s:
                    templates.append(s)
                    eid_labels.append(None)
    elif path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or "EventTemplate" not in reader.fieldnames:
                raise ValueError("CSV file must contain a 'EventTemplate' column.")
            has_event_id_col = "EventId" in (reader.fieldnames or [])
            for row in reader:
                val = row.get("EventTemplate")
                if val is None:
                    continue
                s = str(val).strip()
                if not s:
                    continue
                templates.append(s)
                if has_event_id_col:
                    eid = str(row.get("EventId", "")).strip()
                    eid_labels.append(eid or None)
                else:
                    eid_labels.append(None)
    else:
        raise ValueError("Unsupported template file format. Use .txt or .csv files.")
    return templates, eid_labels


class MatcherParserConfig(CoreParserConfig):
    method_type: str = "matcher_parser"

    remove_spaces: bool = True
    remove_punctuation: bool = True
    lowercase: bool = True

    path_templates: str | None = None


class MatcherParser(CoreParser):
    def __init__(
        self,
        name: str = "MatcherParser",
        config: MatcherParserConfig | dict[str, Any] = MatcherParserConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = MatcherParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)
        self.config: MatcherParserConfig

        if self.config.path_templates is not None:
            raw_templates, eid_labels = load_templates(self.config.path_templates)
        else:
            raw_templates, eid_labels = [], []
        compiled_templates, metadata = _compile_templates(raw_templates, eid_labels)
        self.template_matcher = TemplateMatcher(
            template_list=compiled_templates,
            metadata=metadata,
            remove_spaces=self.config.remove_spaces,
            remove_punctuation=self.config.remove_punctuation,
            lowercase=self.config.lowercase,
        )

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        parsed = self.template_matcher(input_["log"])

        output_["template"] = parsed["EventTemplate"]
        output_["variables"] = parsed["Params"]
        output_["EventID"] = parsed["EventId"]
