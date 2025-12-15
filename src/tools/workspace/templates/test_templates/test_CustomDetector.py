from typing import Any
from detectmatelibrary import schemas
from ..CustomDetector import CustomDetector, CustomDetectorConfig


default_args = {
    "detectors": {
        "CustomDetector": {
            "method_type": "custom_detector",
            "auto_config": False,
            "params": {},
        }
    }
}


class TestCustomDetector:
    def test_initialize_default(self) -> None:
        detector = CustomDetector(name="CustomDetector", config=default_args)
        assert isinstance(detector, CustomDetector)
        assert detector.name == "CustomDetector"
        assert isinstance(detector.config, CustomDetectorConfig)

    def test_run_detect_method(self) -> None:
        detector = CustomDetector()
        data = schemas.ParserSchema({"log": "test log"})
        output: Any = schemas.DetectorSchema()

        result = detector.detect(data, output)

        assert output.description == "Dummy detection process"
        if result:
            assert output.score == 1.0
            assert "Anomaly detected" in output.alertsObtain["type"]
        else:
            assert output.score == 0.0
            assert len(output.alertsObtain) == 0
