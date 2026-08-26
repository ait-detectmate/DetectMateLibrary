"""
Main tests are done at low level in the deeplearning module as DeeplogDetector is an interface.

Tests at this level are only end to end pipeline.
"""

from detectmatelibrary.detectors.deeplog_detector import DeeplogDetector
from detectmatelibrary.parsers.template_matcher import MatcherParser
from detectmatelibrary.helper.from_to import From

from tests.test_data import AUDIT_LOG, AUDIT_TEMPLATES, TRAIN_UNTIL

import detectmatelibrary.schemas as schemas

import pytest


class TestDeeplog:
    @pytest.mark.ignored
    def test_end2end_autoconfig(self) -> None:
        config = {
            "detectors": {
                "DeeplogDetector": {
                    "method_type": "deeplog_detector",
                    "auto_config": True,
                    "data_use_configure": 10,
                    "data_use_training": 10,
                    "window_size": 3, 
                }
            }
        }

        deeplog = DeeplogDetector(config=config)
        assert deeplog.get_state() == "Default"

        for j in range(2):
            for i in [1, 2, 3, 4, 5, 1, 2]:
                deeplog.process(schemas.ParserSchema({"EventID": i}))

            if j == 0:
                assert deeplog.get_state() == "Configuring"
            
        assert deeplog.get_state() == "Training"

        for _ in range(2):
            for i in [1, 2, 3, 4, 5, 1, 2]:
                deeplog.process(schemas.ParserSchema({"EventID": i}))
        assert deeplog.get_state() == "Default"

    @pytest.mark.ignored
    def test_end2end_no_autoconfig(self) -> None:
        config = {
            "detectors": {
                "DeeplogDetector": {
                    "method_type": "deeplog_detector",
                    "auto_config": False,
                    "data_use_training": 10,
                    "window_size": 3, 
                    "hyperparameters": {
                        "Model": {
                            "hidden_dim": 64,
                            "n_layers": 2,
                        },
                        "Train": {
                            "seed": 0,
                            "batch_size": 2048,
                            "learning_rate": 0.01,
                            "epochs": 10,
                            "patience": 3,
                        },
                        "Finetune": [],
                    }
                }
            }
        }

        deeplog = DeeplogDetector(config=config)
        assert deeplog.get_state() == "Default"

        for j in range(2):
            for i in [1, 2, 3, 4, 5, 1, 2]:
                deeplog.process(schemas.ParserSchema({"EventID": i}))
            if j == 0:
                assert deeplog.get_state() == "Training"

        assert deeplog.get_state() == "Default"


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
        "DeeplogDetector": {
            "method_type": "deeplog_detector",
            "auto_config": False,
            "data_use_training": TRAIN_UNTIL,
            "window_size": 3, 
            "hyperparameters": {
                "Model": {
                    "hidden_dim": 64,
                    "n_layers": 2,
                },
                "Train": {
                    "seed": 0,
                    "batch_size": 2048,
                    "learning_rate": 0.01,
                    "epochs": 10,
                    "patience": 3,
                },
                "Finetune": [],
            }
        }
    }
}


class TestDeeplogDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.ignored
    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector = DeeplogDetector(config=PIPELINE_CONFIG)

        detected_ids = set()
        for parsed_log in From.log(parser, in_path=AUDIT_LOG, do_process=True):
            alert = detector.process(parsed_log)
            if detector.get_state() == "Default" and alert is not None:
                detected_ids.update(set([log_id for log_id in alert["logIDs"]]))

        found = True
        for log_id in {'1861', '1862'}:
            if log_id not in detected_ids:
                found = False

        assert found
