
import detectmatelibrary.utils.deep_learning._op as op
import detectmatelibrary.utils.deep_learning.deeplog as deeplog
import detectmatelibrary.utils.deep_learning.logbert as logbert

import pytest

import jax.numpy as jnp
import jax

import sys
from typing import Any


class TestDLOp:
    def test_checkpoint(self) -> None:
        checkpoint = op.CheckPoint(patience=2)

        assert not checkpoint(0.1, 1, {"hi": "is not mee"})
        assert not checkpoint(0.02, 2, {"hi": "is mee"})
        assert not checkpoint(0.2, 2, {"hi": "is not mee"})
        assert checkpoint(0.2, 2, {"hi": "is not mee"})

        epoch, param = checkpoint.load_checkpoint()
        assert epoch == 2
        assert {"hi": "is mee"} == param

    def test_mask(self) -> None:
        mask = op.Mask(seq_size=4, mask_per=0.5)

        mask_tensor_1 = mask(3)

        assert mask_tensor_1.shape == (3, 4)
        for i in range(3):
            assert mask_tensor_1[i].sum() == 2

        mask_tensor_2 = mask(3)

        assert not jnp.array_equal(mask_tensor_1, mask_tensor_2)
        for i in range(3):
            assert mask_tensor_2[i].sum() == 2

    def test_mask_draws_are_unchanged(self) -> None:
        mask = op.Mask(seq_size=10, mask_per=0.4)
        base = jnp.concat([jnp.ones((3, 6)), jnp.zeros((3, 4))], axis=1).astype(jnp.int32)

        for i in range(4):
            expected = jax.random.permutation(jax.random.key(i), base, independent=True, axis=1)
            assert jnp.array_equal(mask(3), expected)
        assert mask.i == 4

    def test_mask_at_is_draw_i_without_advancing(self) -> None:
        drawn = op.Mask(seq_size=10, mask_per=0.4)
        draws = [drawn(3) for _ in range(4)]

        mask = op.Mask(seq_size=10, mask_per=0.4)
        at_jit = jax.jit(mask.at, static_argnums=1)
        for i in range(4):
            assert jnp.array_equal(mask.at(i, 3), draws[i])
            assert jnp.array_equal(at_jit(i, 3), draws[i])
        assert mask.i == 0

    def test_batched_matches_one_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(op, "EVAL_BATCH", 4)
        x, y = jnp.arange(30).reshape(10, 3), jnp.arange(10)
        sizes = []

        def f(x: jnp.ndarray, y: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray]:
            sizes.append(x.shape[0])
            return x.sum(1) * y, -y

        batched = op.batched(f, x, y)
        assert sizes == [4, 4, 2]
        assert all(jnp.array_equal(b, o) for b, o in zip(batched, f(x, y)))
        assert jnp.array_equal(op.batched(lambda x: x.sum(1), x[:0]), x[:0].sum(1))

    def test_smallest_top_k(self) -> None:
        scores = jnp.array([0] * 95 + [3] * 4 + [7])

        assert op.smallest_top_k(scores, alert_rate=0.05) == 1  # the 5 windows ranked 3 or 7 alert
        assert op.smallest_top_k(scores, alert_rate=0.01) == 4  # only the window ranked 7 alerts
        assert op.smallest_top_k(scores, alert_rate=0.0) == 8
        assert op.smallest_top_k(scores, alert_rate=1.0) == 1


def random_windows(n: int, size: int) -> list[tuple[int, ...]]:
    return [tuple(int(v) for v in row) for row in jax.random.randint(jax.random.key(1), (n, size), 0, 6)]


def padded_windows(n: int, size: int) -> list[tuple[int, ...]]:
    """random_windows with the first i % size events of window i set to PAD, as
    at the start of a session."""
    return [(op.PAD,) * (i % size) + w[i % size:] for i, w in enumerate(random_windows(n, size))]


def validation_alert_share(model: Any, top_k: int, windows: list[tuple[int, ...]]) -> float:
    """Share of the validation windows of a training run on windows that
    check_anomaly flags at top_k."""
    _, val_seqs = model._prepare_data(seqs=windows, var_per=0.5)
    seqs = [tuple(int(v) for v in row) for row in val_seqs.reshape(val_seqs.shape[0], -1)]
    return sum(bool(model.check_anomaly(seq, top_k)) for seq in seqs) / len(seqs)


def assert_smallest_top_k_within_alert_rate(
    model: Any, alert_rate: float, windows: list[tuple[int, ...]] | None = None
) -> None:
    """The top_k a training run picks is the smallest at which at most
    alert_rate of its validation windows alert."""
    windows = windows or random_windows(60, 5)
    top_k = model.train(seqs=windows, var_per=0.5)["top_k"]

    assert validation_alert_share(model, top_k, windows) <= alert_rate
    assert top_k == 1 or validation_alert_share(model, top_k - 1, windows) > alert_rate


def validation_stats(monkeypatch: pytest.MonkeyPatch, eval_batch: int, model: Any) -> dict:
    """The validation losses and top_k of a seeded training run on 30 + 30
    windows, and the number of windows in each of its batched passes."""
    monkeypatch.setattr(op, "EVAL_BATCH", eval_batch)
    passes: list[int] = []
    monkeypatch.setattr(
        sys.modules[type(model).__module__], "batched",
        lambda f, *xs: passes.append(xs[0].shape[0]) or op.batched(f, *xs),
    )
    stats = model.train(seqs=random_windows(60, 5), var_per=0.5)
    return {"Loss Val": [float(v) for v in stats["Loss Val"]], "top_k": stats["top_k"], "passes": passes}


def assert_same_stats(in_batches: dict, one_pass: dict) -> None:
    # Another batch shape can round a loss differently in its last float32 digit, depending on the CPU.
    assert in_batches["Loss Val"] == pytest.approx(one_pass["Loss Val"], rel=1e-6)
    assert in_batches["top_k"] == one_pass["top_k"]
    assert in_batches["passes"] == one_pass["passes"]


class TestDeeplog:
    def test_validation_in_batches_matches_one_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "Model": {"hidden_dim": 4, "n_layers": 1},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2},
        }
        one_pass = validation_stats(monkeypatch, 1000, deeplog.DeepLog(config=config))
        assert one_pass["passes"] == [30, 30, 30]  # the loss after each epoch, then top_k
        assert_same_stats(validation_stats(monkeypatch, 7, deeplog.DeepLog(config=config)), one_pass)

    def test_top_k_keeps_validation_alerts_within_alert_rate(self) -> None:
        config = {
            "Model": {"hidden_dim": 4, "n_layers": 1},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2, "alert_rate": 0.1},
        }
        assert_smallest_top_k_within_alert_rate(deeplog.DeepLog(config=config), alert_rate=0.1)

    @pytest.mark.ignored
    def test_deeplog_model(self) -> None:
        model = deeplog.DeepLogModel(hidden_dim=4, n_layers=1, output_size=1)

        x = jnp.ones((3, 4, 1), dtype=jnp.float32)
        params = model.init(jax.random.PRNGKey(0), x[:1])['params']

        y = model.apply({"params": params}, x)
        assert y.shape == (3, 1)

    @pytest.mark.ignored
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

    @pytest.mark.ignored
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


class TestLogBert:
    def test_validation_in_batches_matches_one_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "Model": {"hidden": 4, "n_layers": 1, "num_heads": 1, "dropout": 0.0, "max_len": 10},
            "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": 2},
        }
        one_pass = validation_stats(monkeypatch, 1000, logbert.LogBert(config=config))
        assert one_pass["passes"] == [30, 30, 30]  # the loss after each epoch, then top_k
        assert_same_stats(validation_stats(monkeypatch, 7, logbert.LogBert(config=config)), one_pass)

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

    def test_padding_adds_no_loss(self) -> None:
        model = logbert.LogBertModel(n_embed=6, hidden=4, num_heads=1, n_layers=1, dropout=0.0, max_len=10)
        x = jnp.array(padded_windows(10, 5))
        params = model.init(jax.random.key(0), x)["params"]
        loss_mlkp, _ = logbert.window_losses(model, params, x, jnp.zeros_like(x))  # every event masked

        assert jnp.isfinite(loss_mlkp).all()
        assert (loss_mlkp[x == op.PAD] == 0).all() and (loss_mlkp[x != op.PAD] > 0).all()

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

    @pytest.mark.ignored
    def test_logbert_model(self) -> None:
        model = logbert.LogBertModel(
            n_embed=3, hidden=8, num_heads=1, n_layers=1, dropout=0.0, max_len=10
        )

        params = model.init(jax.random.PRNGKey(0), jnp.zeros((1, 5), dtype=jnp.int32))['params']
        x = jnp.ones((3, 10), dtype=jnp.int32)

        y, dist = model.apply({"params": params}, x)
        assert y.shape == (3, 10, 3)
        assert dist.shape == (3, 8)

    @pytest.mark.ignored
    def test_logbert_train(self) -> None:
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

    @pytest.mark.ignored
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
