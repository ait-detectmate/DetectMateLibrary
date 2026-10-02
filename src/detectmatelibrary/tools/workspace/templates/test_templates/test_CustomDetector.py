from ..CustomDetector import CustomDetector, CustomDetectorConfig
from detectmatelibrary.helper.from_to import From


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
        gen = From.json(detector, "data.json", do_process=False)
        i = 0
        while True:
            try:
                data = next(gen)
            except StopIteration:
                break
            assert detector.process(data) is None
            output = detector.process(data)
            assert output.description == "Dummy detection process"
            assert output.score == 1.0
            assert output.alertsObtain["type"] == "Anomaly detected by MyCoolThing"
            assert output.detectorID == "MyCoolThing"
            assert output.detectorType == "MyCoolThing_detector"
            assert output.alertID == f"MyCoolThing_{i + 10}"
            assert output.logIDs == [str(i)]
            i += 1
