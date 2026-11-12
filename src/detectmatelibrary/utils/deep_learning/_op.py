import jax
import jax.numpy as jnp

from typing import Any, Callable


EVAL_BATCH = 2048


def batched(f: Callable[..., Any], *xs: jnp.ndarray) -> Any:
    """Apply ``f`` to the rows of ``xs`` in batches of ``EVAL_BATCH`` and
    concatenate its outputs (an array or a tuple of arrays).

    For a row-wise ``f`` this gives the values of ``f(*xs)`` without
    holding the model's activations for all rows at once, which for a
    large validation set takes gigabytes.
    """
    outs = [f(*(x[i:i + EVAL_BATCH] for x in xs)) for i in range(0, max(xs[0].shape[0], 1), EVAL_BATCH)]
    return jax.tree.map(lambda *parts: jnp.concatenate(parts), *outs)


def smallest_top_k(scores: jnp.ndarray, alert_rate: float) -> int:
    """Return the smallest ``top_k`` at which at most ``alert_rate`` of the
    windows alert.

    ``scores`` holds one rank per window, 0 being the model's first
    guess. A window alerts at ``top_k`` when its rank is ``top_k`` or
    more.
    """
    allowed = int(alert_rate * scores.shape[0])
    if allowed >= scores.shape[0]:
        return 1
    return int(jnp.sort(scores)[::-1][allowed]) + 1


class CheckPoint:
    def __init__(self, patience: int) -> None:
        self.last_loss = jnp.inf
        self.epoch = -1
        self.param: None | dict[str, Any] = None
        self.patience, self.i = patience, 0

    def __call__(self, loss: float, epoch: int, param: dict[str, Any]) -> bool:
        if self.last_loss > loss or self.param is None:
            self.last_loss = loss
            self.epoch = epoch
            self.param = param
            self.i = 0
        else:
            self.i += 1

        return self.i >= self.patience

    def load_checkpoint(self) -> tuple[int, dict[str, Any] | None]:
        return self.epoch, self.param


class Mask:
    def __init__(self, seq_size: int, mask_per: float) -> None:
        self.i = 0
        self.seq_size = seq_size
        self.mask_per = mask_per
        self.s0 = int(seq_size * mask_per)
        self.s1 = self.seq_size - self.s0

    def at(self, i: int | jnp.ndarray, batch_size: int) -> jnp.ndarray:
        """Return draw number ``i`` without moving the counter.

        ``i`` may be a traced value, so compiled code draws the same
        masks as the calls.
        """
        mask = jnp.concat([
            jnp.ones((batch_size, self.s1)), jnp.zeros((batch_size, self.s0))
        ], axis=1).astype(jnp.int32)

        return jax.random.permutation(jax.random.key(i), mask, independent=True, axis=1)

    def next_draw(self) -> int:
        """Return the number of the next draw and move the counter past it."""
        i = self.i
        self.i += 1
        return i

    def __call__(self, batch_size: int) -> jnp.ndarray:
        return self.at(self.next_draw(), batch_size)
