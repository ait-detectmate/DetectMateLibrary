# --8<-- [start:example]
from detectmatelibrary.detectors.bigram_frequency_detector import BigramFrequencyDetector, BufferMode
import detectmatelibrary.schemas as schemas

cfg = {
    "detectors": {
        "BigramFrequencyTest": {
            "method_type": "bigram_frequency_detector",
            "auto_config": False,
            "params": {},
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

detector = BigramFrequencyDetector(name="BigramFrequencyTest", config=cfg)

parsed_data = schemas.ParserSchema({
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


alert = detector.process(parsed_data)
# --8<-- [end:example]