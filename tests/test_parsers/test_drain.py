"""Most of the functionality is test it in DetectMatePerformance."""
from detectmatelibrary.parsers.drain import DrainParser
from detectmatelibrary import schemas


class TestDrainParser:
    def test_train_process(self):
        config_dict = {
            "parsers": {
                "DrainParser": {
                    "method_type": "drain_parser",
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
