# --8<-- [start:example]
import detectmatelibrary.detectors.rule_detector as rd
from detectmatelibrary import schemas

rule_detector = rd.RuleDetector()

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

alert = rule_detector.process(parser_data)
# --8<-- [end:example]