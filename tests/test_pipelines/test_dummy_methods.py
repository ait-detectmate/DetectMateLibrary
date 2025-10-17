
from detectmatelibrary.detectors.dummy_detector import DummyDetector, DummyDetectorConfig
import detectmatelibrary.schemas as schemas


class TestDummyMethods:
    def test_initialize_default(self) -> None:
        detector = DummyDetector(name="DummyDetector", config={})

        assert isinstance(detector, DummyDetector)
        assert detector.name == "DummyDetector"
        assert isinstance(detector.config, DummyDetectorConfig)

    def test_run_detect_method(self) -> None:
        detector = DummyDetector()
        data = schemas.initialize(schemas.PARSER_SCHEMA, **{"log": "test log"})
        output = schemas.initialize(schemas.DETECTOR_SCHEMA)

        result = detector.detect(data, output)

        assert output.description == "Dummy detection process"
        if result:
            assert output.score == 1.0
            assert "Anomaly detected by DummyDetector" in output.alertsObtain["type"]
        else:
            assert output.score == 0.0
            assert len(output.alertsObtain) == 0
