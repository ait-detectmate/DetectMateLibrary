# --8<-- [start:example]
from detectmatelibrary.detectors.charset_detector import CharsetDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "CharsetTest": {
            "method_type": "charset_detector",
            "auto_config": False,
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{"pos": 0, "name": "var1", "params": {}}],
                    }
                }
            },
        }
    }
}

detector = CharsetDetector(name="CharsetTest", config=cfg)

parsed_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["var1"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"},
})

alert = detector.process(parsed_data)
# --8<-- [end:example]
