# --8<-- [start:example]
from detectmatelibrary.detectors.deeplog_detector import DeeplogDetector

import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "DeeplogDetector": {
            "method_type": "deeplog_detector",
            "auto_config": True,
        }
    }
}

detector = DeeplogDetector(name="DeeplogDetector", config=cfg)

test_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 12,
    "template": "test template",
    "variables": ["adsasd", "asdasd"],
    "logID": "2",
    "parsedLogID": "2",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"level": "CRITICAL"}
})
output = schemas.DetectorSchema()

result = detector.detect(test_data, output)
# --8<-- [end:example]