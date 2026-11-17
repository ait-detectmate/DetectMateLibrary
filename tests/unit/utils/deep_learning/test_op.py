"""Tests for detectmatelibrary.utils.deep_learning._op."""
import detectmatelibrary.utils.deep_learning._op as op

import pytest

import jax.numpy as jnp
import jax


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
