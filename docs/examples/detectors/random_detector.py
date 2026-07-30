# --8<-- [start:example]
from detectmatelibrary.detectors.random_detector import RandomDetector
import detectmatelibrary.schemas as schemas


config = {
    "detectors": {
        "TestDetector": {
            "auto_config": False,
            "method_type": "random_detector",
            "params": {},
            "events": {
                1: {
                    "test": {
                        "params": {},
                        "variables": [{
                            "pos": 0,
                            "name": "process",
                            "params": {
                                "threshold": 0.
                            }
                        }]
                    }
                }
            }
        }
    }
}

# assume `config` is loaded from YAML and converted to the detector Config class
detector = RandomDetector(name="TestDetector", config=config)

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

# process returns True if an alert was emitted, False otherwise
alert_emitted = detector.process(parser_data)
# --8<-- [end:example]