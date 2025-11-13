
from detectmatelibrary.detectors.dummy_detector import DummyDetector, DummyDetectorConfig
from detectmatelibrary.parsers.dummy_parser import DummyParser, DummyParserConfig
import detectmatelibrary.schemas as schemas


default_args = {
    "parsers": {
        "DummyParser": {
            "auto_config": False,
            "method_type": "dummy_parser",
            "params": {},
        }
    },
    "detectors": {
        "DummyDetector": {
            "method_type": "dummy_detector",
            "auto_config": False,
            "params": {},
        }
    }
}


class TestDummyMethods:
    def test_initialize_default(self) -> None:
        detector = DummyDetector(name="DummyDetector", config=default_args)

        assert isinstance(detector, DummyDetector)
        assert detector.name == "DummyDetector"
        assert isinstance(detector.config, DummyDetectorConfig)

    def test_run_detect_method(self) -> None:
        detector = DummyDetector()
        data = schemas.ParserSchema_({"log": "test log"})
        output = schemas.DetectorSchema_()

        result = detector.detect(data, output)

        assert output.description == "Dummy detection process"
        if result:
            assert output.score == 1.0
            assert "Anomaly detected by DummyDetector" in output.alertsObtain["type"]
        else:
            assert output.score == 0.0
            assert len(output.alertsObtain) == 0

    def test_parser_initialize_default(self) -> None:
        parser = DummyParser(name="DummyParser", config=default_args)

        assert isinstance(parser, DummyParser)
        assert parser.name == "DummyParser"
        assert isinstance(parser.config, DummyParserConfig)

    def test_run_parse_method(self) -> None:
        parser = DummyParser()
        input_data = schemas.LogSchema_({"log": "test log"})
        output_data = schemas.ParserSchema_()

        parser.parse(input_data, output_data)

        assert output_data.variables == ["dummy_variable"]
        assert output_data.template == "This is a dummy template"

    def test_pipeline(test) -> None:
        parser = DummyParser()
        detector = DummyDetector()

        log_input = schemas.LogSchema_({"log": "test log"})
        parsed_log = parser.process(log_input)

        while (result := detector.process(parsed_log)) is None:
            pass

        assert result.description == "Dummy detection process"
        assert result.score == 1.
