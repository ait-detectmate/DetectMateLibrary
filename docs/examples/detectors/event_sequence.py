# --8<-- [start:example]
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetector, \
    EventSequenceDetectorConfig
import detectmatelibrary.schemas as schemas

detector = EventSequenceDetector(
    name="EventSequenceTest",
    config=EventSequenceDetectorConfig(auto_config=False, fixed_window_size=3),
)

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
