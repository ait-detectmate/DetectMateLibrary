from detectmatelibrary.parsers.template_matcher._matcher_op import TemplateMatcher
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from typing import Any
import csv
import os


class TemplatesNotFoundError(Exception):
    pass


class TemplateNoPermissionError(Exception):
    pass


class MatcherParserConfig(CoreParserConfig):
    method_type: str = "matcher_parser"

    remove_spaces: bool = True
    remove_punctuation: bool = True
    lowercase: bool = True

    path_templates: str = "<PLACEHOLDER>"


class MatcherParser(CoreParser):
    def __init__(
        self,
        name: str = "MatcherParser",
        config: MatcherParserConfig | dict[str, Any] = MatcherParserConfig(),
    ) -> None:

        if isinstance(config, dict):
            config = MatcherParserConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.template_matcher = TemplateMatcher(
            template_list=self.__load_templates(self.config.path_templates),
            remove_spaces=self.config.remove_spaces,
            remove_punctuation=self.config.remove_punctuation,
            lowercase=self.config.lowercase,
        )

    def __load_templates(self, path: str) -> list[str]:
        if not os.path.exists(path):
            raise TemplatesNotFoundError(f"Templates file not found at: {path}")
        if not os.access(path, os.R_OK):
            raise TemplateNoPermissionError(
                f"You do not have the permission to access the templates file: {path}"
            )
        if path.endswith(".txt"):
            with open(path, "r") as f:
                templates = [line.strip() for line in f if line.strip()]
        elif path.endswith(".csv"):
            templates = []
            # Use the lightweight built-in csv module instead of pandas
            # Expect a header with a 'template' column
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None or "EventTemplate" not in reader.fieldnames:
                    raise ValueError("CSV file must contain a 'EventTemplate' column.")
                for row in reader:
                    val = row.get("EventTemplate")
                    if val is None:
                        continue
                    s = str(val).strip()
                    if s:
                        templates.append(s)
        else:
            raise ValueError("Unsupported template file format. Use .txt or .csv files.")
        return templates

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        parsed = self.template_matcher(input_.log)

        output_.template = parsed["EventTemplate"]
        output_.variables = parsed["Params"]
        output_.EventID = parsed["EventId"]
