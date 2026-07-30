# --8<-- [start:example]
from detectmatelibrary.detectors.new_event_detector import NewEventDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "NewEventTest": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {}
        },
        "MultipleDetector": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {}
        },
        "NewEventDetector": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {}
        }
    }
}

detector = NewEventDetector(name="NewEventTest", config=cfg)

parser_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["var1"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})


alert = detector.process(parser_data)
# --8<-- [end:example]
