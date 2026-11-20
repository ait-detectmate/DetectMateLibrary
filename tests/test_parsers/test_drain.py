"""Most of the functionality is test it in DetectMatePerformance."""
from detectmatelibrary.parsers.drain import DrainParser
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
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, general R2D2!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

    def test_federation_process(self):
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
        parser_1 = DrainParser(config=config_dict)
        parser_2 = DrainParser(config=config_dict)
        parser_1 + parser_2

        parsed = parser_1.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_1.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_1.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parsed = parser_2.process(schemas.LogSchema({"log": "hello world and planets"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_2.process(schemas.LogSchema({"log": "hello world or planets"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_2.process(schemas.LogSchema({"log": "hello world and planets"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello world <*> planets"

        parsed = parser_1.process(schemas.LogSchema({"log": "hello world xor planets"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

        parser_2.aggregate()
        parsed = parser_1.process(schemas.LogSchema({"log": "hello world xor planets"}))
        assert parsed["template"] == "hello world <*> planets"

    def test_federation_process_binary(self):
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
        parser_1 = DrainParser(config=config_dict)
        parser_2 = DrainParser(config=config_dict)
        parser_3 = DrainParser(config=config_dict)

        parsed = parser_1.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_1.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_1.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parsed = parser_2.process(schemas.LogSchema({"log": "hello world and planets"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_2.process(schemas.LogSchema({"log": "hello world or planets"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser_2.process(schemas.LogSchema({"log": "hello world and planets"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello world <*> planets"

        parsed = parser_1.process(schemas.LogSchema({"log": "hello world xor planets"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

        parser_1.stack([parser_3.to_binary(), parser_2.to_binary()])
        parser_1.aggregate()
        parsed = parser_1.process(schemas.LogSchema({"log": "hello world xor planets"}))
        assert parsed["template"] == "hello world <*> planets"

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
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parser.update_state("keep_training")
        parsed = parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
        parser.update_state("stop_training")

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["eventID"] == -1
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
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        parser.update_state("keep_training")
        parsed = parser.process(schemas.LogSchema({"log": "bella ciao bella ciao"}))
        parser.update_state("stop_training")

        parsed = parser.process(schemas.LogSchema({"log": "hello there, sargent kenobi!"}))
        assert parsed["template"] == "hello there <*> kenobi"

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

    def test_auto_config_off_keeps_hyperparameters_through_configure_phase(self):
        """Same data as above, but auto_config off: the hyperparameter search
        must not run, so the configured depth survives."""
        config_dict = {
            "parsers": {
                "DrainParser": {
                    "method_type": "drain_parser",
                    "depth": 2,
                    "max_childs": 10,
                    "sim_thres": 0.2,
                    "auto_config": False,
                    "data_use_configure": 2,
                    "data_use_training": 2,
                }
            }
        }
        parser = DrainParser(config=config_dict)
        parser.process(schemas.LogSchema({"log": "hello there, general kenobi!"}))
        parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))
        parser.process(schemas.LogSchema({"log": "hello there, captain kenobi!"}))

        assert parser.config.depth == 2
        assert parser.config_buffer == []
