import jax
import jax.numpy as jnp

from typing import Any


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

    def __call__(self, batch_size: int) -> jnp.ndarray:
        mask = jnp.concat([
            jnp.ones((batch_size, self.s1)), jnp.zeros((batch_size, self.s0))
        ], axis=1).astype(jnp.int32)

        seed = jax.random.key(self.i)
        self.i += 1

        mask = jax.random.permutation(seed, mask, independent=True, axis=1)
        return mask
