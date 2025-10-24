
from detectmatelibrary.common.detector import CoreDetector
from detectmatelibrary.common.parser import CoreParser

from detectmatelibrary.readers.log_file import LogFileReader

import detectmatelibrary.schemas as schemas

import pytest


config = {
    "readers": {
        "File_reader": {
            "method_type": "log_file_reader",
            "auto_config": False,
            "params": {
                "file": "tests/test_folder/logs.log"
            }
        }
    },
    "parsers": {
        "dummy_parser": {
            "method_type": "core_parser",
            "auto_config": False,
            "params": {}
        }
    },
    "detectors": {
        "dummy_detector": {
            "method_type": "core_detector",
            "auto_config": False,
            "params": {}
        }
    },
}


class MockupBadParser(CoreParser):
    def parse(self, input_, output_):
        input_.log = "This message was change!"

        output_.EventID = 1
        output_.template = "hello"
        output_.variables.extend(["a", "b"])
        output_.logFormatVariables["timestamp"] = "1"


class MockupDetector(CoreDetector):
    def detect(self, input_, output_):
        output_.score = 0.9
        output_.predictionLabel = True
        output_.description = "ciao"


class TestCaseBasicPipelines:
    """This pipelines should not crash."""
    def test_compromise_messages(self) -> None:
        reader = LogFileReader(config=config)

        parser = MockupBadParser(name="dummy_parser", config=config)

        log = reader.process(as_bytes=False)
        msg = log.log
        parser.process(log)

        assert msg == log.log

    def test_get_incorrect_schema(self) -> None:
        reader = LogFileReader(config=config)

        detector = MockupDetector(
            name="dummy_detector",
            config=config,
            buffer_mode="no_buf",
            buffer_size=None,
        )

        log = reader.process(as_bytes=False)
        with pytest.raises(schemas.IncorrectSchema):
            detector.process(log)
