"""
Main tests are done at low level in the deeplearning module as LogBertDetector is an interface.

Tests at this level are only end to end pipeline.
"""

from detectmatelibrary.detectors.logbert_detector import LogBertDetector

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
