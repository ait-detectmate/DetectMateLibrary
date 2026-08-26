# --8<-- [start:example]
from detectmatelibrary.detectors.scvs_detector import SCVSDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "SCVSDetector": {
            "method_type": "scvs_detector",
            "auto_config": False,
        }
    }
}
detector = SCVSDetector(name="SCVSDetector", config=cfg)

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
