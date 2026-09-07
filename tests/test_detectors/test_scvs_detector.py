
from detectmatelibrary.detectors.scvs_detector import SCVSDetector, SCVSDetectorConfig
from detectmatelibrary.utils.sequence_encoding import build_count_vec
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From
from detectmatelibrary import schemas

from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

import pytest


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


PIPELINE_CONFIG = {
    "parsers": {
        "MatcherParser": {
            "method_type": "matcher_parser",
            "auto_config": False,
            "log_format": "type=<Type> msg=audit(<Time>): <Content>",
            "time_format": None,
            "params": {
                "remove_spaces": True,
                "remove_punctuation": True,
                "lowercase": True,
                "path_templates": AUDIT_TEMPLATES,
            },
        }
    },
    "detectors": {
        "SCVSDetector": {
            "method_type": "scvs_detector",
            "window_size": 10,
            "data_use_training": TRAIN_UNTIL,
        }
    }
}


class TestSCVSDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.ignored
    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector = SCVSDetector(config=PIPELINE_CONFIG)

        detected_ids = set()
        for parsed_log in From.log(parser, in_path=AUDIT_LOG, do_process=True):
            alert = detector.process(parsed_log)
            if detector.get_state() == "Default" and alert is not None:
                detected_ids.update(set([log_id for log_id in alert["logIDs"]]))

        for log_id in {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}:
            assert log_id in detected_ids
