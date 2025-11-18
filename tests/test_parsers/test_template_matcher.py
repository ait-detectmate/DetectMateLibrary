
import pytest
from detectmatelibrary.parsers.template_matcher import (
    MatcherParser, MatcherParserConfig, TemplatesNotFoundError
)
from detectmatelibrary import schemas

test_template = [
    "pid=<*> uid=<*> auid=<*> ses=<*> msg='op=PAM:<*> acct=<*>",
]
test_log_match = 'pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting acct="root"'
test_log_no_match = 'this is not matching'


class TestMatcherParserBasic:
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
                    "path_templates": "tests/test_folder/test_templates.txt"
                }
            }
        }
        parser = MatcherParser(name="MatcherParser", config=config_dict)
        input_log = schemas.initialize(schemas.LOG_SCHEMA, **{"log": test_log_match})
        output_data = schemas.initialize(schemas.PARSER_SCHEMA)
        parser.parse(input_log, output_data)

        assert output_data.template == test_template[0]
        assert output_data.EventID == 0
        assert len(output_data.variables) > 0

    def test_no_match(self):
        config_dict = {
            "parsers": {
                "MatcherParser": {
                    "auto_config": True,
                    "method_type": "matcher_parser",
                    "path_templates": "tests/test_folder/test_templates.txt"
                }
            }
        }
        parser = MatcherParser(name="MatcherParser", config=config_dict)
        input_log = schemas.initialize(schemas.LOG_SCHEMA, **{"log": test_log_no_match})
        output_data = schemas.initialize(schemas.PARSER_SCHEMA)
        parser.parse(input_log, output_data)

        assert output_data.template == "<Not Found>"
        assert output_data.EventID == -1
        assert output_data.variables == []

    def test_custom_preprocessing_flags(self):
        config = MatcherParserConfig(
            remove_spaces=False,
            remove_punctuation=False,
            lowercase=False,
            path_templates="tests/test_folder/test_templates.txt"
        )
        parser = MatcherParser(name="MatcherParser", config=config)
        input_log = schemas.initialize(schemas.LOG_SCHEMA, **{"log": test_log_match})
        output_data = schemas.initialize(schemas.PARSER_SCHEMA)
        parser.parse(input_log, output_data)
        # Still matches template even with preprocessing disabled
        assert output_data.template == test_template[0]
