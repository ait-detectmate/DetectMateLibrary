"""Tests for NewEventDetector class.

This module tests the NewEventDetector implementation including:
- Initialization and configuration
- Training functionality to learn known values
- Detection logic for new/unknown values
- Event-specific configuration handling
- Input/output schema validation
"""

from detectmatelibrary.detectors.new_event_detector import NewEventDetector, BufferMode
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
import detectmatelibrary.schemas as schemas

from detectmatelibrary.utils.aux import time_test_mode


# Set time test mode for consistent timestamps
time_test_mode()


config = {
    "detectors": {
        # "CustomInit": {
        #     "method_type": "new_event_detector",
        #     "auto_config": False,
        #     "params": {},
        #     "events": {
        #         1: {
        #             "instance1": {
        #                 "params": {},
        #                 "variables": [{
        #                     "pos": 0, "name": "sad", "params": {}
        #                 }]
        #             }
        #         }
        #     }
        # },
        # "MultipleDetector": {
        #     "method_type": "new_event_detector",
        #     "auto_config": False,
        #     "params": {},
        #     "events": {
        #         1: {
        #             "test": {
        #                 "params": {},
        #                 "variables": [{
        #                     "pos": 1, "name": "test", "params": {}
        #                 }],
        #                 "header_variables": [{
        #                     "pos": "level", "params": {}
        #                 }]
        #             }
        #         }
        #     }
        # },
        "NewEventDetector": {
            "method_type": "new_event_detector",
            "auto_config": False,
            "params": {},
            # "events": {
            #     3: {
            #         "test": {
            #             "params": {},
            #             #"variables": [{
            #             #    "pos": 1, "name": "test", "params": {}
            #             #}],
            #             "header_variables": [{
            #                 "pos": "Type", "params": {}
            #             }]
            #         }
            #     }
            # }
            "events": {}
        }
    }
}


# class TestNewEventDetectorInitialization:
#     """Test NewEventDetector initialization and configuration."""
#
#     def test_default_initialization(self):
#         """Test detector initialization with default parameters."""
#         detector = NewEventDetector()
#
#         assert detector.name == "NewEventDetector"
#         assert hasattr(detector, 'config')
#         assert detector.data_buffer.mode == BufferMode.NO_BUF
#         assert detector.input_schema == schemas.ParserSchema
#         assert detector.output_schema == schemas.DetectorSchema
#         assert hasattr(detector, 'persistency')
#
#     def test_custom_config_initialization(self):
#         """Test detector initialization with custom configuration."""
#         detector = NewEventDetector(name="CustomInit", config=config)
#
#         assert detector.name == "CustomInit"
#         assert hasattr(detector, 'persistency')
#         assert isinstance(detector.persistency.events_data, dict)
#
#
# class TestNewEventDetectorTraining:
#     """Test NewEventDetector training functionality."""
#
#     def test_train_multiple_values(self):
#         """Test training with multiple different values."""
#         detector = NewEventDetector(config=config, name="MultipleDetector")
#         # Train with multiple values (only event 1 should be tracked per config)
#         for event in range(3):
#             for level in ["INFO", "WARNING", "ERROR"]:
#                 parser_data = schemas.ParserSchema({
#                     "parserType": "test",
#                     "EventID": event,
#                     "template": "test template",
#                     "variables": ["0", "assa"],
#                     "logID": "1",
#                     "parsedLogID": "1",
#                     "parserID": "test_parser",
#                     "log": "test log message",
#                     "logFormatVariables": {"level": level}
#                 })
#                 detector.train(parser_data)
#
#         # Only event 1 should be tracked (based on events config)
#         assert len(detector.persistency.events_data) == 1
#         event_data = detector.persistency.get_event_data(1)
#         assert event_data is not None
#         # Check the level values
#         assert "INFO" in event_data["level"].unique_set
#         assert "WARNING" in event_data["level"].unique_set
#         assert "ERROR" in event_data["level"].unique_set
#         # Check the variable at position 1 (named "test")
#         assert "assa" in event_data["test"].unique_set
#
#
# class TestNewEventDetectorDetection:
#     """Test NewEventDetector detection functionality."""
#
#     def test_detect_known_value_no_alert(self):
#         detector = NewEventDetector(config=config, name="MultipleDetector")
#
#         # Train with a value
#         train_data = schemas.ParserSchema({
#             "parserType": "test",
#             "EventID": 1,
#             "template": "test template",
#             "variables": ["adsasd", "asdasd"],
#             "logID": "1",
#             "parsedLogID": "1",
#             "parserID": "test_parser",
#             "log": "test log message",
#             "logFormatVariables": {"level": "INFO"}
#         })
#         detector.train(train_data)
#
#         # Detect with the same value
#         test_data = schemas.ParserSchema({
#             "parserType": "test",
#             "EventID": 12,
#             "template": "test template",
#             "variables": ["adsasd"],
#             "logID": "2",
#             "parsedLogID": "2",
#             "parserID": "test_parser",
#             "log": "test log message",
#             "logFormatVariables": {"level": "CRITICAL"}
#         })
#         output = schemas.DetectorSchema()
#
#         result = detector.detect(test_data, output)
#
#         assert not result
#         assert output.score == 0.0
#
#     def test_detect_known_value_alert(self):
#         detector = NewEventDetector(config=config, name="MultipleDetector")
#
#         # Train with a value
#         train_data = schemas.ParserSchema({
#             "parserType": "test",
#             "EventID": 1,
#             "template": "test template",
#             "variables": ["adsasd", "asdasd"],
#             "logID": "1",
#             "parsedLogID": "1",
#             "parserID": "test_parser",
#             "log": "test log message",
#             "logFormatVariables": {"level": "INFO"}
#         })
#         detector.train(train_data)
#
#         # Detect with the same value
#         test_data = schemas.ParserSchema({
#             "parserType": "test",
#             "EventID": 1,
#             "template": "test template",
#             "variables": ["adsasd", "asdasd"],
#             "logID": "2",
#             "parsedLogID": "2",
#             "parserID": "test_parser",
#             "log": "test log message",
#             "logFormatVariables": {"level": "CRITICAL"}
#         })
#         output = schemas.DetectorSchema()
#
#         result = detector.detect(test_data, output)
#
#         assert result
#         assert output.score == 1.0
#
#
_PARSER_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>:*): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": "tests/test_folder/audit_templates.txt",
            },
        }
    }
}


class TestNewEventDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=_PARSER_CONFIG)
        detector = NewEventDetector(config=config, name="NewEventDetector")

        logs = list(From.log(parser, in_path="tests/test_folder/audit.log", do_process=True))
        print("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", logs[2], type(logs[2]), dir(logs[2]))
        print("GGGGGGGGGGGGGGG", logs[2]["logFormatVariables"])
        print("HHHHHHHHHHHHHHH", logs[2]["variables"])

        for log in logs[:1800]:
            detector.configure(log)
        detector.set_configuration()

        for log in logs[:1800]:
            detector.train(log)

        detected_ids: set[str] = set()
        for log in logs[1800:]:
            output = schemas.DetectorSchema()
            if detector.detect(log, output_=output):
                detected_ids.add(log["logID"])

        #assert detected_ids == {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}
