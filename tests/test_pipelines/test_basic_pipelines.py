from detectmatelibrary.common.detector import CoreDetector, BufferMode
from detectmatelibrary.common.parser import CoreParser

from detectmatelibrary.detectors.new_value_combo_detector import NewValueComboDetector
from detectmatelibrary.detectors.new_value_detector import NewValueDetector
from detectmatelibrary.detectors.random_detector import RandomDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.readers.log_file import LogFileReader

import yaml


class MockupParser(CoreParser):
    def parse(self, input_, output_):
        output_.EventID = 1
        output_.template = "hello"
        output_.variables.extend(["a", "b"])


class MockupDetector(CoreDetector):
    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "ciao"


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


class TestCaseBasicPipelines:
    """This pipelines should not crash."""
    def test_basic_pipeline(self) -> None:
        reader = LogFileReader(config=config)

        parser = MockupParser(name="dummy_parser", config=config)
        detector = MockupDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.NO_BUF,
            buffer_size=None,
        )

        assert (log := reader.process(as_bytes=False)) is not None
        assert (parsed_log := parser.process(log)) is not None
        assert detector.process(parsed_log) is not None

    def test_window_pipeline(self) -> None:
        reader = LogFileReader(config=config)

        parser = MockupParser(name="dummy_parser", config=config)
        detector = MockupDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.WINDOW,
            buffer_size=3,
        )
        for _ in range(2):
            log = reader.process(as_bytes=False)
            parsed_log = parser.process(log)
            assert detector.process(parsed_log) is None

        assert (log := reader.process(as_bytes=False)) is not None
        assert (parsed_log := parser.process(log)) is not None
        assert detector.process(parsed_log) is not None

    def test_batch_pipeline(self) -> None:
        reader = LogFileReader(config=config)

        parser = MockupParser(name="dummy_parser", config=config)
        detector = MockupDetector(
            name="dummy_detector",
            config=config,
            buffer_mode=BufferMode.BATCH,
            buffer_size=3,
        )

        for _ in range(2):
            log = reader.process(as_bytes=False)
            parsed_log = parser.process(log)
            assert detector.process(parsed_log) is None

        assert (log := reader.process(as_bytes=False)) is not None
        assert (parsed_log := parser.process(log)) is not None
        assert detector.process(parsed_log) is not None


class TestExamples:
    def test_config_example(self) -> None:
        with open("config/pipeline_config_default.yaml", 'r') as file:
            config = yaml.safe_load(file)

        # Nothing should crash

        # Readers
        LogFileReader(config=config)

        # Parsers
        MatcherParser(config=config)

        # Detectors
        RandomDetector(config=config)

        NewValueDetector(config=config)
        NewValueDetector(config=config, name="NewValueDetector_All")

        NewValueComboDetector(config=config)
        NewValueComboDetector(config=config, name="NewValueComboDetector_All")
