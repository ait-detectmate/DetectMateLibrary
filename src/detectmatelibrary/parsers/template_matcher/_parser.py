from detectmatelibrary.parsers.template_matcher._matcher_op import TemplateMatcher
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

import os


class TemplatesNotFoundError(Exception):
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
        config: MatcherParserConfig | dict = MatcherParserConfig(),
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

    def __load_templates(self, path: str) -> list[str] | TemplatesNotFoundError:
        if not os.path.exists(path):
            raise TemplatesNotFoundError(f"Template file not found at: {path}")

        with open(path, "r") as f:
            templates = [line.strip() for line in f if line.strip()]
        return templates

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        parsed = self.template_matcher(input_.log)

        output_.template = parsed["EventTemplate"]
        output_.variables.extend(parsed["Params"])
        output_.EventID = parsed["EventId"]
