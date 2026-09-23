"""Most of the functionality is test it in DetectMatePerformance."""
from detectmatelibrary.parsers.autoparser import AutoParser

from detectmatelibrary.helper.from_to import From
import pytest

temp = "pid <*> uid <*> auid <*> ses <*> msg op <*> acct <*> exe <*> hostname <*> addr <*> terminal <*> res <*>"  # noqa: E501


class TestAutoParserParser:
    def test_train_process(self):
        config_dict = {
            "parsers": {
                "AutoParser": {
                    "method_type": "auto_parser",
                    "data_use_training": 10,
                }
            }
        }
        parser = AutoParser(config=config_dict)
        path = "tests/test_data/audit.log"

        for j, parsed_log in enumerate(From.log(parser, path)):
            if j == 15:
                break

        assert parsed_log["template"] == temp

    def test_fix_templates(self):
        config_dict = {
            "parsers": {
                "AutoParser": {
                    "method_type": "auto_parser",
                    "data_use_training": 10,
                    "params": {
                        "fix_type": "BGL"
                    }
                }
            }
        }
        parser = AutoParser(config=config_dict)
        path = "tests/test_data/audit.log"

        for j, parsed_log in enumerate(From.log(parser, path)):
            if j == 15:
                break

        assert parsed_log["template"] == "template not found"

    def test_unknonw_fix_dataset(self):
        config_dict = {
            "parsers": {
                "AutoParser": {
                    "method_type": "auto_parser",
                    "data_use_training": 1,
                    "params": {
                        "fix_type": "Unknown"
                    }
                }
            }
        }
        parser = AutoParser(config=config_dict)
        path = "tests/test_data/audit.log"

        next(From.log(parser, path))
        with pytest.warns():
            next(From.log(parser, path))
