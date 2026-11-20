"""Test the Brain parser's training and configuration lifecycle."""
from detectmatelibrary import schemas
from detectmatelibrary.parsers.brain import BrainParser


TRAINING_LOGS = ("hello there, general kenobi!", "hello there, captain kenobi!")
MATCHING_LOG = "hello there, sergeant kenobi!"
NEW_TRAINING_LOG = "bella ciao bella ciao"


class TestBrainParser:
    def test_train_process(self):
        config_dict = {
            "parsers": {
                "BrainParser": {
                    "method_type": "brain_parser",
                    "params": {"weight": 1.0, "data_use_training": 2},
                },
            },
        }
        parser = BrainParser(config=config_dict)

        for log in TRAINING_LOGS:
            parsed = parser.process(schemas.LogSchema({"log": log}))
            assert parsed["eventID"] == -1
            assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"
        assert list(parsed["variables"]) == ["sergeant"]

        parsed = parser.process(schemas.LogSchema({"log": "hello there, general R2D2!"}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

    def test_reset_after_train(self):
        config_dict = {
            "parsers": {
                "BrainParser": {
                    "method_type": "brain_parser",
                    "params": {
                        "weight": 1.0,
                        "data_use_training": 2,
                        "reset_in_post_train": True,
                    },
                },
            },
        }
        parser = BrainParser(config=config_dict)

        for log in TRAINING_LOGS:
            parser.process(schemas.LogSchema({"log": log}))
        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["template"] == "hello there <*> kenobi"

        parser.update_state("keep_training")
        parser.process(schemas.LogSchema({"log": NEW_TRAINING_LOG}))
        parser.update_state("stop_training")

        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

        parsed = parser.process(schemas.LogSchema({"log": NEW_TRAINING_LOG}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == NEW_TRAINING_LOG

    def test_not_reset_train(self):
        config_dict = {
            "parsers": {
                "BrainParser": {
                    "method_type": "brain_parser",
                    "params": {
                        "weight": 1.0,
                        "data_use_training": 2,
                        "reset_in_post_train": False,
                    },
                },
            },
        }
        parser = BrainParser(config=config_dict)

        for log in TRAINING_LOGS:
            parser.process(schemas.LogSchema({"log": log}))
        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["template"] == "hello there <*> kenobi"

        parser.update_state("keep_training")
        parser.process(schemas.LogSchema({"log": NEW_TRAINING_LOG}))
        parser.update_state("stop_training")

        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["eventID"] >= 0
        assert parsed["template"] == "hello there <*> kenobi"

        parsed = parser.process(schemas.LogSchema({"log": NEW_TRAINING_LOG}))
        assert parsed["eventID"] >= 0
        assert parsed["template"] == NEW_TRAINING_LOG

    def test_auto_config_selects_hyperparameters(self):
        config_dict = {
            "parsers": {
                "BrainParser": {
                    "method_type": "brain_parser",
                    "auto_config": True,
                    "params": {
                        "weight": 1.0,
                        "data_use_configure": 2,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = BrainParser(config=config_dict)

        for log in (*TRAINING_LOGS, MATCHING_LOG):
            parser.process(schemas.LogSchema({"log": log}))

        assert parser.config.weight == 0.5

    def test_auto_config_off_keeps_hyperparameters_through_configure_phase(self):
        config_dict = {
            "parsers": {
                "BrainParser": {
                    "method_type": "brain_parser",
                    "auto_config": False,
                    "params": {
                        "weight": 1.0,
                        "data_use_configure": 2,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = BrainParser(config=config_dict)

        for log in (*TRAINING_LOGS, MATCHING_LOG):
            parser.process(schemas.LogSchema({"log": log}))

        assert parser.config.weight == 1.0
        assert parser.parser_gen.weight == 1.0
        assert parser.config_buffer == []
