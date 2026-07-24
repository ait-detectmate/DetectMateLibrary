
from detectmatelibrary.detectors.scvs_detector import build_count_vec, SCVSDetector, SCVSDetectorConfig
from detectmatelibrary import schemas


class TestSCVSDetector:
    def test_build_count_vec(self):
        input_ = [
            schemas.ParserSchema({"EventID": i}) for i in [0, 1, 4, 0]
        ]
        expected = tuple([2, 1, 0, 0, 1])

        assert build_count_vec(input_) == expected

    def test_window_size(self):
        ecvc = SCVSDetector(config=SCVSDetectorConfig(window_size=10))
        assert ecvc.get_window_size() == 10

        ecvc = SCVSDetector(config=SCVSDetectorConfig(window_size=7))
        assert ecvc.get_window_size() == 7

    def test_scvs(self):
        config = {
            "detectors": {
                "SCVSDetector": {
                    "method_type": "scvs_detector",
                    "window_size": 3,
                    "data_use_training": 30,
                }
            }
        }

        scvs = SCVSDetector(config=config)

        input_ = []
        for _ in range(10):
            input_.extend([schemas.ParserSchema({"EventID": i}) for i in [0, 1, 4, 0]])

        for in_ in input_:
            scvs.process(in_)
        assert scvs.get_state() == "Default"

        for in_ in input_[5:15]:
            alert = scvs.process(in_)
        assert alert is None

        for in_ in [schemas.ParserSchema({"EventID": i}) for i in [4, 4, 4, 4, 4, 4, 1, 0, 1, 1]]:
            alert = scvs.process(in_)
        assert alert is not None
