
from detectmatelibrary.common.variable_detector import VariableDetector
import detectmatelibrary.schemas as schemas


CONFIG = {
    "detectors": {
        "detector": {
            "method_type": "variable_detector",
            "auto_config": False,
            "params": {
                "allow_fed": True,
            },
            "events": {
                1: {
                    "i": {
                        "params": {},
                        "variables": [{"pos": 0, "name": "user", "params": {}}]
                    }
                }
            },
        }
    }
}


def train(detector: VariableDetector, *users) -> None:
    for u in users:
        detector.train(schemas.ParserSchema({
            "parserType": "t", "EventID": 1, "template": "t", "variables": [u],
            "logID": "1", "parsedLogID": "1", "parserID": "p", "log": "l",
            "logFormatVariables": {},
        }))


class TestFederation:
    def test_train(self):
        detector1 = VariableDetector(name="detector", config=CONFIG)
        train(detector1, "A", "B", "C")

        users = detector1.persistency.get_event_data(1)["user"].unique_set
        assert {"A", "B", "C"} == users
        assert len(detector1.persistency.event_struct.get_data()) == 3

    def test_agregate_strategy_stack(self):
        detector1 = VariableDetector(name="detector", config=CONFIG)
        detector2 = VariableDetector(name="detector", config=CONFIG)

        train(detector1, "A", "B", "C")
        train(detector2, "B", "D")

        assert len(detector1.persistency.event_struct.get_data()) == 3
        assert len(detector2.persistency.event_struct.get_data()) == 2

        detector1.stack(detector2)
        detector1.aggregate()
        print("detector1", detector1.persistency.event_struct.get_data())

        users = detector1.persistency.get_event_data(1)["user"].unique_set
        assert {"A", "B", "C", "D"} == users
        assert len(detector1.persistency.event_struct.get_data()) == 5

    def test_agregate_strategy_first(self):
        detector1 = VariableDetector(name="detector", config=CONFIG)
        detector2 = VariableDetector(name="detector", config=CONFIG)
        detector3 = VariableDetector(name="detector", config=CONFIG)
        detector1 + detector2 + detector3

        train(detector1, "A", "B", "C")
        train(detector2, "B", "D")
        train(detector3, "B", "E")

        detector1.aggregate()
        assert len(detector1.persistency.event_struct.get_data()) == 7

        users = detector2.persistency.get_event_data(1)["user"].unique_set
        assert {"A", "B", "C", "D", "E"} == users

    def test_agregate_strategy_stack_binary(self):
        detector1 = VariableDetector(name="detector", config=CONFIG)
        detector2 = VariableDetector(name="detector", config=CONFIG)

        train(detector1, "A", "B", "C")
        train(detector2, "B", "D")

        detector1.stack(detector2.to_binary())
        result = detector1.aggregate()

        detector3 = VariableDetector(name="detector", config=CONFIG)
        detector3 = detector3.from_binary(result)

        users = detector3.persistency.get_event_data(1)["user"].unique_set
        assert {"A", "B", "C", "D"} == users
