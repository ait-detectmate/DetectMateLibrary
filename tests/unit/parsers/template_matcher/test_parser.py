"""Tests for detectmatelibrary.parsers.template_matcher._parser."""
import os

import pytest
from detectmatelibrary.parsers.template_matcher import MatcherParser, MatcherParserConfig, \
    TemplatesNotFoundError
from detectmatelibrary.parsers.template_matcher._parser import (
    TemplateNoPermissionError, _compile_templates, load_templates,
)

from detectmatelibrary.common._config._formats import EventsConfig
from detectmatelibrary import schemas
from tests.support.paths import NAMED_TEMPLATES_TXT, NAMED_TEMPLATES_CSV, TEST_TEMPLATES


test_template = ["pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>"]
test_log_match = 'pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting acct="root"'
test_log_no_match = 'this is not matching'


class TestMatcherParserBasic:
    def test_no_path_templates(self):
        config_dict = {
            "parsers": {
                "MatcherParser": {
                    "auto_config": True,
                    "method_type": "matcher_parser",
                }
            }
        }
        parser = MatcherParser(name="MatcherParser", config=config_dict)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == "<Not Found>"
        assert output_data.eventID == -1
        assert output_data.variables == []

    def test_templates_not_found(self):
        config_dict = {
            "parsers": {
                "MatcherParser": {
                    "auto_config": True,
                    "method_type": "matcher_parser",
                    "path_templates": "non_existent_file.txt"
                }
            }
        }
        with pytest.raises(TemplatesNotFoundError):
            MatcherParser(name="MatcherParser", config=config_dict)

    def test_successful_match(self):
        config_dict = {
            "parsers": {
                "MatcherParser": {
                    "auto_config": True,
                    "method_type": "matcher_parser",
                    "path_templates": TEST_TEMPLATES
                }
            }
        }
        parser = MatcherParser(name="MatcherParser", config=config_dict)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == test_template[0]
        assert output_data.eventID == 0
        assert len(output_data.variables) > 0

    def test_no_match(self):
        config_dict = {
            "parsers": {
                "MatcherParser": {
                    "auto_config": True,
                    "method_type": "matcher_parser",
                    "path_templates": TEST_TEMPLATES
                }
            }
        }
        parser = MatcherParser(name="MatcherParser", config=config_dict)
        input_log = schemas.LogSchema({"log": test_log_no_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == "<Not Found>"
        assert output_data.eventID == -1
        assert output_data.variables == []

    def test_custom_preprocessing_flags(self):
        config = MatcherParserConfig(
            remove_spaces=False,
            remove_punctuation=False,
            lowercase=False,
            path_templates=TEST_TEMPLATES
        )
        parser = MatcherParser(name="MatcherParser", config=config)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)
        # Still matches template even with preprocessing disabled
        assert output_data.template == test_template[0]


class TestCompileTemplates:
    def test_named_wildcards_compiled_to_anon(self):
        raw = ["pid=<pid> uid=<uid> auid=<auid>"]
        compiled, metadata = _compile_templates(raw)
        assert compiled == ["pid=<*> uid=<*> auid=<*>"]
        assert metadata[0]["labels"] == ["pid", "uid", "auid"]
        assert metadata[0]["event_id_label"] is None

    def test_anonymous_wildcards_unchanged(self):
        raw = ["pid=<*> uid=<*>"]
        compiled, metadata = _compile_templates(raw)
        assert compiled == ["pid=<*> uid=<*>"]
        assert metadata[0]["labels"] == []
        assert metadata[0]["event_id_label"] is None

    def test_event_id_label_stored(self):
        raw = ["pid=<pid> uid=<uid>"]
        eid_labels: list[str | None] = ["login_failure"]
        compiled, metadata = _compile_templates(raw, eid_labels)
        assert compiled == ["pid=<*> uid=<*>"]
        assert metadata[0]["event_id_label"] == "login_failure"
        assert metadata[0]["labels"] == ["pid", "uid"]

    def test_mixing_raises_value_error(self):
        raw = ["pid=<*> uid=<uid>"]
        with pytest.raises(ValueError, match="mixes"):
            _compile_templates(raw)

    def test_multiple_templates(self):
        raw = ["pid=<pid> uid=<uid>", "arch=<*> syscall=<*>"]
        compiled, metadata = _compile_templates(raw)
        assert compiled[0] == "pid=<*> uid=<*>"
        assert compiled[1] == "arch=<*> syscall=<*>"
        assert metadata[0]["labels"] == ["pid", "uid"]
        assert metadata[1]["labels"] == []


class TestNamedWildcardsTxt:
    """Named wildcards in .txt template files (event IDs remain positional)."""

    named_template_compiled = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>"

    def test_match_produces_correct_variables(self):
        config = MatcherParserConfig(path_templates=NAMED_TEMPLATES_TXT)
        parser = MatcherParser(name="MatcherParser", config=config)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == self.named_template_compiled
        assert output_data.eventID == 0
        assert len(output_data.variables) == 6

    def test_compile_resolves_named_positions(self):
        config = MatcherParserConfig(path_templates=NAMED_TEMPLATES_TXT)
        parser = MatcherParser(name="MatcherParser", config=config)

        raw_events: dict = {
            0: {
                "my_detector": {
                    "params": {},
                    "variables": [
                        {"pos": "pid"},
                        {"pos": "op"},
                    ]
                }
            }
        }
        events_config = EventsConfig._init(raw_events)
        compiled = parser.template_matcher.compile_detector_config(events_config)

        # pid is label 0 → pos 0; op is label 4 → pos 4
        resolved_vars = compiled.events[0].variables
        assert 0 in resolved_vars
        assert resolved_vars[0].name == "pid"
        assert 4 in resolved_vars
        assert resolved_vars[4].name == "op"

    def test_compile_unknown_label_raises(self):
        config = MatcherParserConfig(path_templates=NAMED_TEMPLATES_TXT)
        parser = MatcherParser(name="MatcherParser", config=config)

        raw_events: dict = {
            0: {"d": {"params": {}, "variables": [{"pos": "nonexistent"}]}}
        }
        events_config = EventsConfig._init(raw_events)
        with pytest.raises(ValueError, match="nonexistent"):
            parser.template_matcher.compile_detector_config(events_config)


class TestNamedEventIdCsv:
    """Named event IDs via CSV EventId column."""

    named_template_compiled = "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>"

    def test_match_produces_correct_variables(self):
        config = MatcherParserConfig(path_templates=NAMED_TEMPLATES_CSV)
        parser = MatcherParser(name="MatcherParser", config=config)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == self.named_template_compiled
        assert output_data.eventID == 0
        assert len(output_data.variables) == 6

    def test_compile_resolves_named_event_key(self):
        config = MatcherParserConfig(path_templates=NAMED_TEMPLATES_CSV)
        parser = MatcherParser(name="MatcherParser", config=config)

        raw_events: dict = {
            "login_failure": {
                "my_detector": {
                    "params": {},
                    "variables": [
                        {"pos": "pid"},
                        {"pos": "uid"},
                    ]
                }
            }
        }
        events_config = EventsConfig._init(raw_events)
        compiled = parser.template_matcher.compile_detector_config(events_config)

        # "login_failure" → int key 0
        assert 0 in compiled.events
        resolved_vars = compiled.events[0].variables
        assert 0 in resolved_vars and resolved_vars[0].name == "pid"
        assert 1 in resolved_vars and resolved_vars[1].name == "uid"

    def test_positional_int_event_key_still_works(self):
        config = MatcherParserConfig(path_templates=NAMED_TEMPLATES_CSV)
        parser = MatcherParser(name="MatcherParser", config=config)

        raw_events: dict = {
            0: {"d": {"params": {}, "variables": [{"pos": 0, "name": "process_id"}]}}
        }
        events_config = EventsConfig._init(raw_events)
        compiled = parser.template_matcher.compile_detector_config(events_config)

        assert 0 in compiled.events
        assert compiled.events[0].variables[0].name == "process_id"


class TestLoadTemplates:
    def test_a_csv_names_event_ids_and_skips_empty_templates(self, tmp_path):
        path = tmp_path / "t.csv"
        path.write_text('EventId,EventTemplate\nlogin,"user <*>"\nempty,\n,"host <*>"\n')
        assert load_templates(str(path)) == (["user <*>", "host <*>"], ["login", None])

    def test_a_csv_without_event_ids_gives_positional_ids(self, tmp_path):
        path = tmp_path / "t.csv"
        path.write_text('EventTemplate\n"user <*>"\n')
        assert load_templates(str(path)) == (["user <*>"], [None])

    def test_a_csv_without_templates_is_rejected(self, tmp_path):
        path = tmp_path / "t.csv"
        path.write_text("EventId,Template\nlogin,user <*>\n")
        with pytest.raises(ValueError, match="EventTemplate"):
            load_templates(str(path))

    def test_other_file_types_are_rejected(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_text("[]")
        with pytest.raises(ValueError, match="Unsupported template file format"):
            load_templates(str(path))

    @pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
    def test_an_unreadable_file_is_a_permission_error(self, tmp_path):
        path = tmp_path / "t.txt"
        path.write_text("user <*>\n")
        path.chmod(0)
        with pytest.raises(TemplateNoPermissionError):
            load_templates(str(path))
