"""Most of the functionality is test it in DetectMatePerformance."""
from detectmatelibrary.parsers.tree_matcher import TemplateTreeMatcher
from detectmatelibrary import schemas


test_template = [
    "pid <*> uid <*> auid <*> ses <*> msg op PAM <*> acct <*>",
]
test_log_match = 'pid=9699 uid=0 auid=4294967295 ses=4294967295 msg=\'op=PAM:accounting acct="root"'
test_log_no_match = 'this is not matching'


class TestMatcherParserBasic:
    def test_no_path_templates(self):
        config_dict = {
            "parsers": {
                "TreeMatcher": {
                    "method_type": "tree_matcher",
                }
            }
        }
        parser = TemplateTreeMatcher(name="TreeMatcher", config=config_dict)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == "template not found"
        assert output_data.EventID == -1
        assert output_data.variables == [""]

    def test_successful_match(self):
        config_dict = {
            "parsers": {
                "TreeMatcher": {
                    "method_type": "tree_matcher",
                    "path_templates": "tests/test_folder/test_templates.txt"
                }
            }
        }
        parser = TemplateTreeMatcher(name="TreeMatcher", config=config_dict)
        input_log = schemas.LogSchema({"log": test_log_match})
        output_data = schemas.ParserSchema()
        parser.parse(input_log, output_data)

        assert output_data.template == test_template[0]
        assert output_data.EventID == 0
        assert len(output_data.variables) > 0
