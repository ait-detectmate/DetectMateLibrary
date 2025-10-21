
from detectmatelibrary.parsers.template_matcher import (
    TemplateMatcher, MatcherParser, TemplatesNotFoundError
)
from detectmatelibrary import schemas

import pandas as pd


log_df = pd.read_csv("tests/test_folder/logs_with_template_labels.csv")
test_template = ["pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>"]
test_log = ['pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting acct="root"']


class TestParsing:
    def test_TemplateMatcher_matched(self):
        template_matcher = TemplateMatcher(test_template)
        assert template_matcher.match_logs(test_log)["EventTemplate"][0] == test_template[0]

    def test_TemplateMatcher_unmatched(self):
        log = 'this is not matching'
        template_matcher = TemplateMatcher(test_template)
        assert not template_matcher.match_logs([log])["EventTemplate"][0] == test_template[0]

    def test_Apache_logs(self):
        templates = log_df["EventTemplate"].unique().tolist()
        template_matcher = TemplateMatcher(templates)
        matched_logs_df = template_matcher.match_logs([])
        assert matched_logs_df["EventTemplate"].notnull().all()

    def test_TemplateMatcher_with_params(self):
        logs_df = pd.DataFrame(test_log, columns=['Content'])
        template_matcher = TemplateMatcher(test_template)
        matched_df = template_matcher.match_logs_with_params(logs_df)

        assert matched_df["EventTemplate"][0] == test_template[0]
        assert matched_df["Params"][0] == [
            '9699', '0', '4294967295', '4294967295', 'accounting', 'root'
        ]
        assert matched_df["EventId"][0] == 0


class TestMatcher:
    def test_no_template_found(self) -> None:
        try:
            MatcherParser(config={"path_templates": "non_existent_file.txt"})
        except TemplatesNotFoundError as e:
            assert str(e) == "Template file not found at: non_existent_file.txt"

    def test_matcher_parser(self) -> None:
        matcher_parser = MatcherParser(
            config={"path_templates": "tests/test_folder/test_templates.txt"}
        )
        input_log = schemas.initialize(
            schemas.LOG_SCHEMA, **{"log": test_log[0]}
        )
        output_data = schemas.initialize(schemas.PARSER_SCHEMA)
        matcher_parser.parse(input_log, output_data)

        assert output_data.EventID == 0
        assert output_data.variables == [
            '9699', '0', '4294967295', '4294967295', 'accounting', 'root'
        ]
        assert output_data.template == test_template[0]
