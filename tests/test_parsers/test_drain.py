"""Most of the functionality is test it in DetectMatePerformance."""
from detectmatelibrary.parsers.drain import DrainParser, _found_ratio

from detectmateperformance.match_tree import TreeMatcher
from detectmateperformance.types_ import LogTemplates

from detectmatelibrary import schemas


class TestDrainParser:
    def test_train_process(self):
        config_dict = {
            "parsers": {
                "DrainParser": {
                    "method_type": "drain_parser",
                    "depth": 2,
                    "max_childs": 10,
                    "sim_thres": 0.2,
                    "data_use_training": 2,
                }
            }
        }
        parser = DrainParser(config=config_dict)

        parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["EventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, general R2D2!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "template not found"

    def test_reset_after_train(self):
        config_dict = {
            "parsers": {
                "DrainParser": {
                    "method_type": "drain_parser",
                    "depth": 2,
                    "max_childs": 10,
                    "sim_thres": 0.2,
                    "data_use_training": 2,
                    "reset_in_post_train": True,
                }
            }
        }
        parser = DrainParser(config=config_dict)

        parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["EventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parser.update_state("keep_training")
        parsed = parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
        parser.update_state("stop_training")

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "template not found"

    def test_not_reset_train(self):
        config_dict = {
            "parsers": {
                "DrainParser": {
                    "method_type": "drain_parser",
                    "depth": 2,
                    "max_childs": 10,
                    "sim_thres": 0.2,
                    "data_use_training": 2,
                    "reset_in_post_train": False,
                }
            }
        }
        parser = DrainParser(config=config_dict)

        parsed = parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["EventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["EventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parser.update_state("keep_training")
        parsed = parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
        parser.update_state("stop_training")

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["template"] == "hello there <*> kenobi"

    def test_not_ration_found(self):
        tree_matcher = TreeMatcher(LogTemplates(["hello there <*> kenobi"]))

        logs = ["hello there general kenobi", "akuna matata"]
        assert 0.5 == _found_ratio(logs, tree_matcher)

        logs = ["hello there general kenobi"]
        assert 0. == _found_ratio(logs, tree_matcher)

    def test_no_auto_config_but_no_initialization(self):
        config_dict = {
            "parsers": {
                "DrainParser": {
                    "method_type": "drain_parser",
                    "depth": 2,
                    "max_childs": 10,
                    "sim_thres": 0.2,
                    "auto_config": True,
                    "data_use_configure": 2,
                    "data_use_training": 2,
                }
            }
        }
        parser = DrainParser(config=config_dict)
        parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))

        assert parser.config.depth == 1
        assert parser.config.max_childs == 10
        assert parser.config.sim_thres == 0.2
