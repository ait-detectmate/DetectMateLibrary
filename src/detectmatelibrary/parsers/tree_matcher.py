from detectmatelibrary.common.parser import CoreParser, CoreParserConfig
from detectmatelibrary import schemas

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.types_ import LogTemplates

from typing import Any


class TreeMatcherConfig(CoreParserConfig):
    method_type: str = "tree_matcher"

    path_templates: str | None = None


class TreeMatcherParser(CoreParser):
    def __init__(
        self,
        name: str = "TreeMatcher",
        config: TreeMatcherConfig | dict[str, Any] = TreeMatcherConfig()
    ) -> None:

        if isinstance(config, dict):
            config = TreeMatcherConfig.from_dict(config, name)
        super().__init__(name=name, config=config)

        self.config: TreeMatcherConfig
        if self.config.path_templates is None:
            self.tree = TreeMatcher(LogTemplates([]))
        else:
            self.tree = TreeMatcher.from_file(self.config.path_templates)

    def parse(
        self,
        input_: schemas.LogSchema,
        output_: schemas.ParserSchema
    ) -> None:

        parsed = self.tree.match_log(input_["log"], get_vars=True)

        output_["EventID"] = parsed.get_all_events_ids()[0]
        values = parsed[0]
        output_["variables"].extend(values[1].split(" "))
        output_["template"] = values[0]
