
from src.components.common.parser import CoreParser, CoreParserConfig

from src.components.readers.log_file import LogFileConfig, LogFileReader


class MockupBadParser(CoreParser):
    def parse(self, input_, output_):
        input_.log = "This message was change!"

        output_.EventID = 1
        output_.template = "hello"
        output_.variables.extend(["a", "b"])
        output_.logFormatVariables["timestamp"] = "1"


class TestCaseBasicPipelines:
    """This pipelines should not crash."""
    def test_compromise_messages(self) -> None:
        reader = LogFileReader(
            config=LogFileConfig(file="tests/test_folder/logs.log")
        )
        parser = MockupBadParser(config=CoreParserConfig(
            parserType="TestParserType"
        ))

        log = reader.process(as_bytes=False)
        msg = log.log
        parser.process(log)

        assert msg == log.log
