"""
Main tests are done at low level in the deeplearning module as LogBertDetector is an interface.

Tests at this level are only end to end pipeline.
"""

from detectmatelibrary.detectors.logbert_detector import LogBertDetector
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
                "LogBertDetector": {
                    "method_type": "logbert_detector",
                    "auto_config": True,
                    "data_use_configure": 10,
                    "data_use_training": 10,
                    "window_size": 4, 
                }
            }
        }

        logbert = LogBertDetector(config=config)
        assert logbert.get_state() == "Default"

        for j in range(2):
            for i in [1, 2, 3, 4, 5, 1, 2]:
                logbert.process(schemas.ParserSchema({"EventID": i}))

            if j == 0:
                assert logbert.get_state() == "Configuring"
            
        assert logbert.get_state() == "Training"

        for _ in range(2):
            for i in [1, 2, 3, 4, 5, 1, 2]:
                logbert.process(schemas.ParserSchema({"EventID": i}))
        assert logbert.get_state() == "Default"
        
    @pytest.mark.ignored
    def test_end2end_no_autoconfig(self) -> None:
        config = {
            "detectors": {
                "LogBertDetector": {
                    "method_type": "logbert_detector",
                    "auto_config": False,
                    "data_use_training": 10,
                    "window_size": 4, 
                    "hyperparameters": {
                        "Model": {
                            "hidden": 256,
                            "num_heads": 2,
                            "n_layers": 4,
                            "dropout": 0.0,
                            "max_len": 1000,
                        },
                        "Train": {
                            "seed": 0,
                            "batch_size": 256,
                            "learning_rate": 0.01,
                            "epochs": 10,
                            "mask_per": 0.4,
                            "alpha": 0.0,
                            "patience": 3,
                        },
                        "Finetune": [],
                    }
                }
            }
        }

        logbert = LogBertDetector(config=config)
        assert logbert.get_state() == "Default"

        for j in range(2):
            for i in [1, 2, 3, 4, 5, 1, 2]:
                logbert.process(schemas.ParserSchema({"EventID": i}))
            if j == 0:
                assert logbert.get_state() == "Training"

        assert logbert.get_state() == "Default"


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
        "LogBertDetector": {
            "method_type": "logbert_detector",
            "auto_config": False,
            "data_use_training": TRAIN_UNTIL,
            "window_size": 10, 
            "hyperparameters": {
                "Model": {
                    "hidden": 256,
                    "num_heads": 2,
                    "n_layers": 4,
                    "dropout": 0.0,
                    "max_len": 1000,
                },
                "Train": {
                    "seed": 0,
                    "batch_size": 256,
                    "learning_rate": 0.01,
                    "epochs": 10,
                    "mask_per": 0.4,
                    "alpha": 0.0,
                    "patience": 3,
                },
                "Finetune": [],
            }
        }
    }
}


class TestLogBertDetectorEndToEnd:
    """Regression test: full configure/train/detect pipeline on audit.log."""

    @pytest.mark.ignored
    def test_audit_log_anomalies(self):
        parser = MatcherParser(config=PIPELINE_CONFIG)
        detector = LogBertDetector(config=PIPELINE_CONFIG)

        detected_ids = set()
        for parsed_log in From.log(parser, in_path=AUDIT_LOG, do_process=True):
            alert = detector.process(parsed_log)
            if detector.get_state() == "Default" and alert is not None:
                detected_ids.update(set([log_id for log_id in alert["logIDs"]]))

        found = True
        for log_id in {'1859', '1860', '1861', '1862', '1864', '1865', '1866', '1867'}:
            if log_id not in detected_ids:
                print(log_id)
                found = False

        assert found
