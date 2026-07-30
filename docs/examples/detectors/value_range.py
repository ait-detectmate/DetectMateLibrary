# --8<-- [start:example]
from detectmatelibrary.detectors.value_range_detector import ValueRangeDetector, BufferMode
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "ValueRangeTest": {
            "method_type": "value_range_detector",
            "auto_config": False,
            "params": {"ignore_non_numerical_val": False},
            "events": {
                1: {
                    "instance1": {
                        "params": {},
                        "variables": [{
                            "pos": 1, "name": "myvar", "params": {}
                        }]
                    }
                }
            }
        }
    }
}


detector = ValueRangeDetector(name="ValueRangeTest", config=cfg)

parser_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["1", "2", "17"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})


alert = detector.process(parser_data)
# --8<-- [end:example]