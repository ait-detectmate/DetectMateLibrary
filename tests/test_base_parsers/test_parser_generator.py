from detectmatelibrary.bases.base_parsers.parser_generator import (
    _found_ratio, ParserGenerator, ParserGeneratorConfig
)
from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.types_ import LogTemplates

import detectmatelibrary.schemas as sc


class TestBaseParser:
    def test_not_ration_found(self):
        tree_matcher = TreeMatcher(LogTemplates(["hello there <*> kenobi"]))

        logs = ["hello there general kenobi", "akuna matata"]
        assert 0.5 == _found_ratio(logs, tree_matcher)

        logs = ["hello there general kenobi"]
        assert 0. == _found_ratio(logs, tree_matcher)

    def test_apply_format_variable(self):
        parser = ParserGenerator("test", config=ParserGeneratorConfig(
            log_format="<Ignore> - <Content>", data_use_training=1
        ))

        parser.process(sc.LogSchema({"log": "abcsd - this is the content", "logID": "A"}))
        assert parser.parser_gen.buffer == ["this is the content"]

    def test_apply_format_variable_conf(self):
        parser = ParserGenerator("test", config=ParserGeneratorConfig(
            log_format="<Ignore> - <Content>", data_use_configure=2, auto_config=True
        ))

        parser.process(sc.LogSchema({"log": "abcsd - this is the content", "logID": "A"}))
        assert parser.config_buffer == ["this is the content"]
