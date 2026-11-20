from detectmatelibrary.bases.base_parsers.parser_generator import _found_ratio

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.types_ import LogTemplates


class TestBaseParser:
    def test_not_ration_found(self):
        tree_matcher = TreeMatcher(LogTemplates(["hello there <*> kenobi"]))

        logs = ["hello there general kenobi", "akuna matata"]
        assert 0.5 == _found_ratio(logs, tree_matcher)

        logs = ["hello there general kenobi"]
        assert 0. == _found_ratio(logs, tree_matcher)
