# --8<-- [start:example]
from detectmatelibrary.detectors.ecvc_detector import ECVCDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "ECVCDetector": {
            "method_type": "ecvc_detector_detector",
            "window_size": 10,
            "validation_per": 0.2,
            "threshold_method": "mean"  # mean, default (default = threshold 0)
        }
    }
}
detector = ECVCDetector(name="ECVCDetector", config=cfg)

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
