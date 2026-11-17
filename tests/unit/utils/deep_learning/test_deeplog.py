"""Tests for detectmatelibrary.utils.deep_learning.deeplog."""
import detectmatelibrary.utils.deep_learning.deeplog as deeplog
import pytest
import jax.numpy as jnp
import jax
from tests.support.deep_learning import (
    assert_same_stats,
    assert_smallest_top_k_within_alert_rate,
    validation_stats,
)


class TestDeeplog:
    @pytest.mark.slow
    def test_validation_in_batches_matches_one_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "Model": {"hidden_dim": 4, "n_layers": 1},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2},
        }
        one_pass = validation_stats(monkeypatch, 1000, deeplog.DeepLog(config=config))
        assert one_pass["passes"] == [30, 30, 30]  # the loss after each epoch, then top_k
        assert_same_stats(validation_stats(monkeypatch, 7, deeplog.DeepLog(config=config)), one_pass)

    @pytest.mark.slow
    def test_top_k_keeps_validation_alerts_within_alert_rate(self) -> None:
        config = {
            "Model": {"hidden_dim": 4, "n_layers": 1},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2, "alert_rate": 0.1},
        }
        assert_smallest_top_k_within_alert_rate(deeplog.DeepLog(config=config), alert_rate=0.1)

    @pytest.mark.slow
    def test_deeplog_model(self) -> None:
        model = deeplog.DeepLogModel(hidden_dim=4, n_layers=1, output_size=1)

        x = jnp.ones((3, 4, 1), dtype=jnp.float32)
        params = model.init(jax.random.PRNGKey(0), x[:1])['params']

        y = model.apply({"params": params}, x)
        assert y.shape == (3, 1)

    @pytest.mark.slow
    def test_deeplog_train(self) -> None:
        config = {
            "Model": {
                "hidden_dim": 4,
                "n_layers": 1,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
        }
        deeplog_ = deeplog.DeepLog(config=config)
        stats = deeplog_.train(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert not deeplog_.check_anomaly((1, 2, 0, 1), stats["top_k"])
        assert deeplog_.check_anomaly((1, 2, 2, 0), stats["top_k"])

    @pytest.mark.slow
    def test_deeplog_finetune(self) -> None:
        config = {
            "Model": {
                "hidden_dim": 8,
                "n_layers": 1,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
            "Finetune": [
                ("Model", "hidden_dim", [4, 5])
            ]
        }
        deeplog_ = deeplog.DeepLog(config=config)
        deeplog_.finetune(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert deeplog_.config != config
