# --8<-- [start:example]
from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "NewValueTest": {
            "method_type": "new_value_combo_detector",
            "auto_config": False,
            "auto_config_params": {
                "max_combo_size": 4
            },
            "events": {
                1: {
                    "instance1": {
                        "params": {},
                        "variables": [{
                            "pos": 0, "name": "sad", "params": {}
                        }]
                    }
                }
            }
        }

    }
}

detector = NewValueComboDetector(name="NewValueTest", config=cfg)

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
