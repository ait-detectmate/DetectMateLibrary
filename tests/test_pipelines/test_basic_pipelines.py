from detectmatelibrary.common.detector import CoreDetector, CoreDetectorConfig
from detectmatelibrary.common.parser import CoreParser, CoreParserConfig

from detectmatelibrary.readers.log_file import LogFileConfig, LogFileReader


class MockupParser(CoreParser):
    def parse(self, input_, output_):
        output_.EventID = 1
        output_.template = "hello"
        output_.variables.extend(["a", "b"])
        output_.logFormatVariables["timestamp"] = "1"


class MockupDetector(CoreDetector):
    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "ciao"


class TestCaseBasicPipelines:
    """This pipelines should not crash."""
    def test_basic_pipeline(self) -> None:
        reader = LogFileReader(
            config=LogFileConfig(file="tests/test_folder/logs.log")
        )
        parser = MockupParser(config=CoreParserConfig(
            parserType="TestParserType"
        ))
        detector = MockupDetector(
            config=CoreDetectorConfig(
                detectorID="TestID",
                detectorType="TestDetectorType",
            ),
            buffer_mode="no_buf",
            buffer_size=None,
        )

        assert (log := reader.process(as_bytes=False)) is not None
        assert (parsed_log := parser.process(log)) is not None
        assert detector.process(parsed_log) is not None

    def test_window_pipeline(self) -> None:
        reader = LogFileReader(
            config=LogFileConfig(file="tests/test_folder/logs.log")
        )
        parser = MockupParser(config=CoreParserConfig(
            parserType="TestParserType"
        ))
        detector = MockupDetector(
            config=CoreDetectorConfig(
                detectorID="TestID",
                detectorType="TestDetectorType",
            ),
            buffer_mode="window",
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
        reader = LogFileReader(
            config=LogFileConfig(file="tests/test_folder/logs.log")
        )
        parser = MockupParser(config=CoreParserConfig(
            parserType="TestParserType"
        ))
        detector = MockupDetector(
            config=CoreDetectorConfig(
                detectorID="TestID",
                detectorType="TestDetectorType",
            ),
            buffer_mode="batch",
            buffer_size=3,
        )

        for _ in range(2):
            log = reader.process(as_bytes=False)
            parsed_log = parser.process(log)
            assert detector.process(parsed_log) is None

        assert (log := reader.process(as_bytes=False)) is not None
        assert (parsed_log := parser.process(log)) is not None
        assert detector.process(parsed_log) is not None
