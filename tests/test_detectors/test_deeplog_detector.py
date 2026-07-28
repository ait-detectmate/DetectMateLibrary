"""
Main tests are done at low level in the deeplearning module as DeeplogDetector is an interface.

Tests at this level are only end to end pipeline.
"""

from detectmatelibrary.detectors.deeplog_detector import DeeplogDetector

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
