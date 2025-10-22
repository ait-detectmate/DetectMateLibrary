
from detectmatelibrary.parsers.template_matcher._matcher_op import (
    Preprocess, TemplateMatcher, TemplatesManager
)
from detectmatelibrary.parsers.template_matcher._parser import TemplatesNotFoundError
from detectmatelibrary.parsers.template_matcher._extractor import ParamExtractor
from detectmatelibrary.parsers.template_matcher import MatcherParser

from detectmatelibrary import schemas

import pandas as pd


log_df = pd.read_csv("tests/test_folder/logs_with_template_labels.csv")
test_template = [
    "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>",
    "pid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>",
]
test_log = 'pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting acct="root"'


class TestExtractParamsIfMatchTests:
    def test_handle_trivial_cases(self):
        assert ParamExtractor._handle_trivial_cases("", []) == []
        assert ParamExtractor._handle_trivial_cases("nonempty", []) is None
        assert ParamExtractor._handle_trivial_cases("token", ["token"]) == []
        assert ParamExtractor._handle_trivial_cases("nottoken", ["token"]) is None
        assert ParamExtractor._handle_trivial_cases("", ["token1", "token2"]) == "CONTINUE"

    def test_anchor_start(self):
        assert ParamExtractor._anchor_start("hello world", ["hello", "world"]) == 5
        assert ParamExtractor._anchor_start("hello world", ["hi", "world"]) is None
        assert ParamExtractor._anchor_start("hello world", ["", "world"]) == 0

    def test_handle_last_token(self):
        matched, param, new_pos = ParamExtractor._handle_last_token("hello world", 6, "world")
        assert matched is True
        assert param == ""
        assert new_pos == 11

        matched, param, new_pos = ParamExtractor._handle_last_token("hello world", 6, "planet")
        assert matched is False

        matched, param, new_pos = ParamExtractor._handle_last_token("hello world", 6, "")
        assert matched is True
        assert param == "world"
        assert new_pos == 11

    def test_handle_middle_token(self):
        matched, param, new_pos = ParamExtractor._handle_middle_token("hello world", 0, " world")
        assert matched is True
        assert param == "hello"
        assert new_pos == 11

        matched, param, new_pos = ParamExtractor._handle_middle_token("hello world", 0, " planet")
        assert matched is False

        matched, param, new_pos = ParamExtractor._handle_middle_token("hello world", 0, "")
        assert matched is True
        assert param == ""
        assert new_pos == 0

    def test_matching(self):
        template_tokens = ['pid', 'uid', 'auid', 'ses', 'msgoppam', 'acct', '']
        log = "pid9699uid0auid4294967295ses4294967295msgoppamaccountingacctroot"
        params = ParamExtractor.extract(log, template_tokens)
        expected_params = ['9699', '0', '4294967295', '4294967295', 'accounting', 'root']

        assert params == expected_params

    def test_non_matching(self):
        template_tokens = ['pid', 'uid', 'auid', 'ses', 'msgoppam', 'acct', '']
        log = "this log does not match"
        params = ParamExtractor.extract(log, template_tokens)

        assert params is None


class TestPreprocessing:
    def test_remove_punctuation(self):
        preprocessor = Preprocess(re_spaces=False, re_punctuation=True, do_lowercase=False)
        processed_log = preprocessor(test_log)
        expected_log = "pid9699 uid0 auid4294967295 ses4294967295 msgopPAMaccounting acctroot"
        assert processed_log == expected_log

    def test_remove_extra_spaces(self):
        preprocessor = Preprocess(re_spaces=False, re_punctuation=False, do_lowercase=False)
        processed_log = preprocessor(test_log.replace(" ", "        "))
        elog = "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting acct=\"root\""
        assert processed_log == elog

    def test_to_lowercase(self):
        preprocessor = Preprocess(re_spaces=False, re_punctuation=False, do_lowercase=True)
        processed_log = preprocessor(test_log.upper())
        elog = "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=pam:accounting acct=\"root\""
        assert processed_log == elog

    def test_all_preprocessing(self):
        preprocessor = Preprocess(re_spaces=True, re_punctuation=True, do_lowercase=True)
        processed_log = preprocessor(test_log.upper().replace(" ", "      "))
        elog = "pid9699uid0auid4294967295ses4294967295msgoppamaccountingacctroot"
        assert processed_log == elog


class TestTemplatesManager:
    def test_loading_templates(self):
        manager = TemplatesManager(template_list=test_template)
        assert len(manager.templates) == 2
        assert manager.templates[0]["raw"] == test_template[0]
        assert manager.templates[0]["count"] == 0
        assert manager.templates[0]["min_len"] > 0
        assert isinstance(manager.templates[0]["tokens"], list)

    def test_candidate_indices(self):
        manager = TemplatesManager(template_list=test_template)
        pre_s, candidates = manager.candidate_indices(test_log)
        assert pre_s == manager.preprocess(test_log)
        assert candidates == [0, 1]


class TestParsing:
    def test_TemplateMatcher_matched(self):
        template_matcher = TemplateMatcher(test_template)
        assert template_matcher(test_log)["EventTemplate"] == test_template[0]

    def test_TemplateMatcher_unmatched(self):
        log = 'this is not matching'
        template_matcher = TemplateMatcher(test_template)
        assert not template_matcher(log)["EventTemplate"] == test_template[0]

    def test_TemplateMatcher_with_params(self):
        template_matcher = TemplateMatcher(test_template)
        matched_df = template_matcher(test_log)

        assert matched_df["EventTemplate"] == test_template[0]
        assert matched_df["Params"] == [
            '9699', '0', '4294967295', '4294967295', 'accounting', 'root'
        ]
        assert matched_df["EventId"] == 0


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
            schemas.LOG_SCHEMA, **{"log": test_log}
        )
        output_data = schemas.initialize(schemas.PARSER_SCHEMA)
        matcher_parser.parse(input_log, output_data)

        assert output_data.EventID == 0
        assert output_data.variables == [
            '9699', '0', '4294967295', '4294967295', 'accounting', 'root'
        ]
        assert output_data.template == test_template[0]

    def test_matcher_parser_no_match(self) -> None:
        matcher_parser = MatcherParser(
            config={"path_templates": "tests/test_folder/test_templates.txt"}
        )
        input_log = schemas.initialize(
            schemas.LOG_SCHEMA, **{"log": "this log does not match"}
        )
        output_data = schemas.initialize(schemas.PARSER_SCHEMA)
        matcher_parser.parse(input_log, output_data)

        assert output_data.EventID == -1
        assert output_data.variables == []
        assert output_data.template == "<Not Found>"
