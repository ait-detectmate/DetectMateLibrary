"""Test training, federation, and configuration for the AECID PG parser."""
from detectmatelibrary import schemas
from detectmatelibrary.parsers.aecid_pg import AECIDPGParser


TRAINING_LOGS = ("hello there, general kenobi!", "hello there, captain kenobi!")
MATCHING_LOG = "hello there, sergeant kenobi!"
NEW_TRAINING_LOG = "bella ciao bella ciao"
PEER_TRAINING_LOGS = ("hello world and planets", "hello world or planets")
PEER_MATCHING_LOG = "hello world xor planets"


class TestAECIDPGParser:
    def test_train_process(self):
        config_dict = {
            "parsers": {
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)

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

    def test_federation_process(self):
        config_dict = {
            "parsers": {
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)
        peer = AECIDPGParser(config=config_dict)
        parser + peer

        for log in TRAINING_LOGS:
            parsed = parser.process(schemas.LogSchema({"log": log}))
            assert parsed["eventID"] == -1
            assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        for log in PEER_TRAINING_LOGS:
            parsed = peer.process(schemas.LogSchema({"log": log}))
            assert parsed["eventID"] == -1
            assert parsed["template"] == "templates not yet generated"

        parsed = peer.process(schemas.LogSchema({"log": PEER_MATCHING_LOG}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello world <*> planets"

        parsed = parser.process(schemas.LogSchema({"log": PEER_MATCHING_LOG}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

        peer.aggregate()
        parsed = parser.process(schemas.LogSchema({"log": PEER_MATCHING_LOG}))
        assert parsed["template"] == "hello world <*> planets"
        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["template"] == "hello there <*> kenobi"

    def test_federation_process_binary(self):
        config_dict = {
            "parsers": {
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)
        peer = AECIDPGParser(config=config_dict)
        empty_peer = AECIDPGParser(config=config_dict)

        for log in TRAINING_LOGS:
            parsed = parser.process(schemas.LogSchema({"log": log}))
            assert parsed["eventID"] == -1
            assert parsed["template"] == "templates not yet generated"

        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello there <*> kenobi"

        for log in PEER_TRAINING_LOGS:
            parsed = peer.process(schemas.LogSchema({"log": log}))
            assert parsed["eventID"] == -1
            assert parsed["template"] == "templates not yet generated"

        parsed = peer.process(schemas.LogSchema({"log": PEER_MATCHING_LOG}))
        assert parsed["eventID"] == 0
        assert parsed["template"] == "hello world <*> planets"

        parsed = parser.process(schemas.LogSchema({"log": PEER_MATCHING_LOG}))
        assert parsed["eventID"] == -1
        assert parsed["template"] == "template not found"

        parser.stack([empty_peer.to_binary(), peer.to_binary()])
        parser.aggregate()
        parsed = parser.process(schemas.LogSchema({"log": PEER_MATCHING_LOG}))
        assert parsed["template"] == "hello world <*> planets"
        parsed = parser.process(schemas.LogSchema({"log": MATCHING_LOG}))
        assert parsed["template"] == "hello there <*> kenobi"

    def test_reset_after_train(self):
        config_dict = {
            "parsers": {
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_training": 2,
                        "reset_in_post_train": True,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)

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
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_training": 2,
                        "reset_in_post_train": False,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)

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

    def test_auto_config_selects_hyperparameters(self):
        config_dict = {
            "parsers": {
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "auto_config": True,
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_configure": 2,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)

        for log in (*TRAINING_LOGS, MATCHING_LOG):
            parser.process(schemas.LogSchema({"log": log}))

        assert parser.config.theta_1 == 0.01
        assert parser.config.theta_2 == 0.7
        assert parser.config.theta_3 == 0.4

    def test_auto_config_off_keeps_hyperparameters_through_configure_phase(self):
        config_dict = {
            "parsers": {
                "AECIDPGParser": {
                    "method_type": "aecid_pg_parser",
                    "auto_config": False,
                    "params": {
                        "theta_1": 0.6,
                        "theta_2": 0.8,
                        "theta_3": 0.5,
                        "data_use_configure": 2,
                        "data_use_training": 2,
                    },
                },
            },
        }
        parser = AECIDPGParser(config=config_dict)

        for log in (*TRAINING_LOGS, MATCHING_LOG):
            parser.process(schemas.LogSchema({"log": log}))

        assert parser.config.theta_1 == 0.6
        assert parser.config.theta_2 == 0.8
        assert parser.config.theta_3 == 0.5
        assert parser.config_buffer == []
