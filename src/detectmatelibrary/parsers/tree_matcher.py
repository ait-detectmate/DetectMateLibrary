from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.types_ import LogTemplates

from typing import Any


class TemplateCppTreeMatcherConfig(CoreParserConfig):
    method_type: str = "tree_matcher"

    path_templates: str | None = None


class TemplateCppTreeMatcher(CoreParser):
    def __init__(
        self,
        name: str = "TreeMatcher",
        config: TemplateCppTreeMatcherConfig | dict[str, Any] = TemplateCppTreeMatcherConfig()
    ) -> None:

        if isinstance(config, dict):
            config = TemplateCppTreeMatcherConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.config: TemplateCppTreeMatcherConfig
        if self.config.path_templates is None:
            self.tree = TreeMatcher(LogTemplates([]))
        else:
            self.tree = TreeMatcher.from_file(self.config.path_templates)

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        parsed = self.tree.match_log(input_["log"], get_var=True)[0]

        output_["EventID"] = parsed["EventID"]
        output_["variables"].extend(parsed["ParamList"])
        output_["template"] = parsed["Template"]
