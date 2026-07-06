
from detectmatelibrary.common.detector import CoreDetector, BufferMode
from detectmatelibrary.common.parser import CoreParser

import detectmatelibrary.schemas._classes as schema_classes
from detectmatelibrary.helper.from_to import From

import pytest


config = {
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

log_path = "tests/test_folder/logs.log"


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

        parser = MockupBadParser(name="dummy_parser", config=config)

        log = next(From.log(parser, log_path, do_process=False))
        msg = log.log
        parser.process(log)

        assert msg == log.log

    def test_get_incorrect_schema(self) -> None:

        detector = MockupDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.NO_BUF,
            buffer_size=None,
        )

        with pytest.raises(schema_classes.FieldNotFound):
            next(From.log(detector, log_path))
