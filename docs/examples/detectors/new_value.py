# --8<-- [start:example]

from detectmatelibrary.detectors.new_value_detector import NewValueDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "NewValueTest": {
            "method_type": "new_value_detector",
            "auto_config": False,
            "params": {},
        }
    }
}
detector = NewValueDetector(name="NewValueTest", config=cfg)

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
