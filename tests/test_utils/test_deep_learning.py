
import detectmatelibrary.utils.deep_learning._op as op
import detectmatelibrary.utils.deep_learning.deeplog as deeplog
import detectmatelibrary.utils.deep_learning.logbert as logbert

from functools import lru_cache
import copy

import numpy as np
import pytest

import jax.numpy as jnp
import jax


def _event_log(n: int, n_events: int, seed: int) -> list[int]:
    """A cyclic event log 0, 1, ..., n_events - 1, 0, ... with 10% of the
    events replaced at random."""
    rng = np.random.default_rng(seed)
    log = np.arange(n) % n_events
    noisy = rng.random(n) < 0.1
    log[noisy] = rng.integers(0, n_events, noisy.sum())
    return [int(e) for e in log]


def _windows(log: list[int], size: int) -> list[tuple[int, ...]]:
    return [tuple(log[i:i + size]) for i in range(len(log) - size + 1)]


def _check_windows(size: int, n_events: int, seed: int) -> list[tuple[int, ...]]:
    """About 330 windows to score: normal and random ones, then repeats of
    recent windows (cache hits) and of the first ones (evicted from
    check_anomaly's 128-entry cache, so scored again)."""
    rng = np.random.default_rng(seed)
    normal = _windows(_event_log(200, n_events, seed), size)[:100]
    random_ = [tuple(int(e) for e in rng.integers(0, n_events, size)) for _ in range(150)]
    first = [(normal + random_)[i] for i in rng.permutation(250)]
    return first + first[-40:] + first[:40]


class EagerDeepLog(deeplog.DeepLog):
    """DeepLog's check_anomaly as it was before compilation (the reference)."""

    @lru_cache
    def check_anomaly(self, seq: tuple[int], top_k: int) -> bool:
        if not self.model_trained:
            return False

        seq = jnp.array(seq)
        x, y = seq[:-1], seq[-1]
        top_pred = jnp.argsort(
            self.model.apply({"params": self.params}, x[None, ..., None]).flatten(),
            descending=True
        )
        return not jnp.isin(y, top_pred[:top_k])


class EagerLogBert(logbert.LogBert):
    """LogBERT's check_anomaly (with Mask.__call__ inlined) as it was before
    compilation (the reference)."""

    @lru_cache
    def check_anomaly(self, seq: tuple[int], top_k: int) -> int:
        if self.model is None:
            return False

        x = jnp.array([seq])
        mask = jnp.concat([
            jnp.ones((x.shape[0], self.mask.s1)), jnp.zeros((x.shape[0], self.mask.s0))
        ], axis=1).astype(jnp.int32)
        seed = jax.random.key(self.mask.i)
        self.mask.i += 1
        m = jax.random.permutation(seed, mask, independent=True, axis=1)

        y, _ = self.model.apply({"params": self.params}, x * m, training=False)
        idx = jnp.nonzero(m == 0)
        pred, y = jnp.argsort(y[idx], axis=1, descending=True), x[idx]

        pred = pred[:, :top_k]
        score = 0
        for i in range(pred.shape[0]):
            score += not bool(jnp.isin(y[i], pred[i]))
        return score


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


class TestDeeplog:
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
    def test_compiled_check_anomaly_matches_eager(self) -> None:
        config = {
            "Model": {"hidden_dim": 8, "n_layers": 1},
            "Train": {"batch_size": 32, "learning_rate": 0.01, "epochs": 3},
        }
        deeplog_ = deeplog.DeepLog(config=config)
        stats = deeplog_.train(seqs=_windows(_event_log(400, 6, seed=0), 6), var_per=0.2)

        eager = EagerDeepLog(config=deeplog_.config)
        eager.model, eager.params, eager.model_trained = deeplog_.model, deeplog_.params, True

        windows = _check_windows(size=6, n_events=6, seed=1)
        compiled_alerts = [deeplog_.check_anomaly(w, stats["top_k"]) for w in windows]
        eager_alerts = [eager.check_anomaly(w, stats["top_k"]) for w in windows]

        assert len(windows) == 330
        assert compiled_alerts == eager_alerts
        assert all(type(alert) is bool for alert in compiled_alerts)
        assert 0 < sum(compiled_alerts) < len(windows)
        assert deeplog_._scorer._cache_size() == 1  # traced once for all windows

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
    def test_compiled_check_anomaly_matches_eager(self) -> None:
        config = {
            "Model": {"hidden": 8, "num_heads": 2, "n_layers": 1, "dropout": 0.0, "max_len": 20},
            "Train": {"batch_size": 32, "learning_rate": 0.01, "epochs": 3, "mask_per": 0.4},
        }
        logbert_ = logbert.LogBert(config=config)
        stats = logbert_.train(seqs=_windows(_event_log(400, 6, seed=0), 10), var_per=0.2)
        first_draw = logbert_.mask.i
        assert first_draw > 0  # training and get_best_k moved the shared counter

        eager = EagerLogBert(config=logbert_.config)
        eager.model, eager.params = logbert_.model, logbert_.params
        eager.mask = copy.deepcopy(logbert_.mask)
        logbert.LogBert.check_anomaly.cache_clear()

        windows = _check_windows(size=10, n_events=6, seed=1)
        compiled_scores = [logbert_.check_anomaly(w, stats["top_k"]) for w in windows]
        eager_scores = [eager.check_anomaly(w, stats["top_k"]) for w in windows]

        assert len(windows) == 330
        assert compiled_scores == eager_scores
        assert all(type(score) is int for score in compiled_scores)
        assert len(set(compiled_scores)) > 1
        # One draw per uncached call, as before: fewer draws than calls (cache hits).
        assert logbert_.mask.i == eager.mask.i
        assert first_draw < logbert_.mask.i < first_draw + len(windows)
        assert logbert_._scorer._cache_size() == 1  # traced once for all windows

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
