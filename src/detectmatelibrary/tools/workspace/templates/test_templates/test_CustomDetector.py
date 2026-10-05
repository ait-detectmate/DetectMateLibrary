import os
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
        if os.path.exists("data.json"):
            gen = From.json(detector, "data.json", do_process=False)
        else:
            gen = From.json(detector, os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "../data/parsed_log.json"), do_process=False)
        i = 0
        while True:
            try:
                data = next(gen)
            except StopIteration:
                break
            assert detector.process(data) is None
            output = detector.process(data)
            assert getattr(output, "description") == "Dummy detection process"
            assert getattr(output, "score") == 1.0
            assert getattr(output, "alertsObtain")["type"] == "Anomaly detected by CustomDetector"
            assert getattr(output, "detectorID") == "CustomDetector"
            assert getattr(output, "detectorType") == "custom_detector"
            assert getattr(output, "alertID") == f"CustomDetector_{i + 10}"
            assert getattr(output, "logIDs") == [str(i)]
            i += 1
