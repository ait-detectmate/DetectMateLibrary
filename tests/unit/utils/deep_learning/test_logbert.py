"""Tests for detectmatelibrary.utils.deep_learning.logbert."""
import detectmatelibrary.utils.deep_learning._op as op
import detectmatelibrary.utils.deep_learning.logbert as logbert
import pytest
import jax.numpy as jnp
import jax
from tests.support.deep_learning import (
    assert_same_stats,
    assert_smallest_top_k_within_alert_rate,
    logbert_detection_draws,
    padded_windows,
    random_windows,
    validation_stats,
)


class TestLogBert:
    @pytest.mark.slow
    def test_detection_masks_do_not_depend_on_training_length(self) -> None:
        # Otherwise where early stopping lands, which can differ across CPUs, changes the alerts.
        assert logbert_detection_draws(epochs=1) == logbert_detection_draws(epochs=3) == [0, 1, 2]

    @pytest.mark.slow
    def test_validation_in_batches_matches_one_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "Model": {"hidden": 4, "n_layers": 1, "num_heads": 1, "dropout": 0.0, "max_len": 10},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2},
        }
        one_pass = validation_stats(monkeypatch, 1000, logbert.LogBert(config=config))
        assert one_pass["passes"] == [30, 30, 30]  # the loss after each epoch, then top_k
        assert_same_stats(validation_stats(monkeypatch, 7, logbert.LogBert(config=config)), one_pass)

    @pytest.mark.slow
    def test_top_k_keeps_validation_alerts_within_alert_rate(self) -> None:
        # mask_per 1.0 masks every event, so each mask draw is the same and check_anomaly
        # sees the masks that picked top_k.
        config = {
            "Model": {"hidden": 4, "n_layers": 1, "num_heads": 1, "dropout": 0.0, "max_len": 10},
            "Train": {
                "batch_size": 8, "learning_rate": 0.01, "epochs": 2, "mask_per": 1.0, "alert_rate": 0.1
            },
        }
        assert_smallest_top_k_within_alert_rate(logbert.LogBert(config=config), alert_rate=0.1)

    @pytest.mark.slow
    def test_padding_adds_no_loss(self) -> None:
        model = logbert.LogBertModel(n_embed=6, hidden=4, num_heads=1, n_layers=1, dropout=0.0, max_len=10)
        x = jnp.array(padded_windows(10, 5))
        params = model.init(jax.random.key(0), x)["params"]
        loss_mlkp, _ = logbert.window_losses(model, params, x, jnp.zeros_like(x))  # every event masked

        assert jnp.isfinite(loss_mlkp).all()
        assert (loss_mlkp[x == op.PAD] == 0).all() and (loss_mlkp[x != op.PAD] > 0).all()

    @pytest.mark.slow
    def test_padding_is_not_scored(self) -> None:
        # At top_k = n_embed every event is among the predictions, so only padding could miss.
        config = {
            "Model": {"hidden": 4, "n_layers": 1, "num_heads": 1, "dropout": 0.0, "max_len": 10},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2, "mask_per": 1.0},
        }
        model = logbert.LogBert(config=config)
        model.train(seqs=random_windows(60, 5), var_per=0.5)
        n_embed = model.config["Model"]["n_embed"]

        assert [model.check_anomaly(w, n_embed) for w in padded_windows(10, 5)] == [0] * 10

    @pytest.mark.slow
    def test_top_k_keeps_padded_validation_alerts_within_alert_rate(self) -> None:
        config = {
            "Model": {"hidden": 4, "n_layers": 1, "num_heads": 1, "dropout": 0.0, "max_len": 10},
            "Train": {
                "batch_size": 8, "learning_rate": 0.01, "epochs": 2, "mask_per": 1.0, "alert_rate": 0.1
            },
        }
        assert_smallest_top_k_within_alert_rate(
            logbert.LogBert(config=config), alert_rate=0.1, windows=padded_windows(60, 5)
        )

    @pytest.mark.slow
    def test_logbert_model(self) -> None:
        model = logbert.LogBertModel(
            n_embed=3, hidden=8, num_heads=1, n_layers=1, dropout=0.0, max_len=10
        )

        params = model.init(jax.random.PRNGKey(0), jnp.zeros((1, 5), dtype=jnp.int32))['params']
        x = jnp.ones((3, 10), dtype=jnp.int32)

        y, dist = model.apply({"params": params}, x)
        assert y.shape == (3, 10, 3)
        assert dist.shape == (3, 8)

    @pytest.mark.slow
    def test_logbert_train(self) -> None:
        # mask_per 1.0 masks every event, so the anomalous one is always checked.
        config = {
            "Model": {
                "hidden": 4,
                "n_layers": 1,
                "num_heads": 4,
                "dropout": 0.0,
                "max_len": 10,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
                "mask_per": 1.0,
            },
        }
        logbert_ = logbert.LogBert(config=config)
        stats = logbert_.train(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert not logbert_.check_anomaly((1, 2, 0, 1), stats["top_k"])
        assert logbert_.check_anomaly((1, 2, 3, 0), stats["top_k"])

    @pytest.mark.slow
    def test_logbert_finetune(self) -> None:
        config = {
            "Model": {
                "hidden": 4,
                "n_layers": 1,
                "num_heads": 1,
                "dropout": 0.0,
                "max_len": 10,
            },
            "Train": {
                "batch_size": 3,
                "learning_rate": 0.01,
                "epochs": 2,
            },
            "Finetune": [
                ("Model", "n_layers", [2, 3])
            ]
        }
        logbert_ = logbert.LogBert(config=config)
        logbert_.finetune(
            seqs=[
                [1, 2, 0, 1] for _ in range(4)
            ],
            var_per=0.25
        )
        assert logbert_.config != config
