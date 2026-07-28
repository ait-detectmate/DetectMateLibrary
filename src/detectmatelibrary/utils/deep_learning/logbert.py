
import jax.numpy as jnp
import jax

import flax.linen as nn
import optax

from functools import lru_cache

from dataclasses import dataclass
from typing import Any
from tqdm import tqdm
from math import ceil

from detectmatelibrary.utils.deep_learning._op import CheckPoint, Mask
from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary.utils.finetune import Combinations

import logging


class PositionEmbedding(nn.Module):
    """
    Equation:
        pi,2j = sin(i / 10000^(2j/d))
        pi,2j+1 = cos(i / 10000^(2j/d))
    """
    hidden: int
    max_len: int = 1000

    def setup(self) -> None:
        x = jnp.arange(self.max_len, dtype=jnp.float32).reshape(-1, 1)
        jd = jnp.power(10000, jnp.arange(0, self.hidden, 2, dtype=jnp.float32) / self.hidden)

        position = jnp.zeros((1, self.max_len, self.hidden))
        position = position.at[:, :, 0::2].set(jnp.sin(x / jd))
        position = position.at[:, :, 1::2].set(jnp.cos(x / jd))
        self.position = position

    @nn.compact
    def __call__(self, X: jnp.ndarray) -> jnp.ndarray:
        X = X + self.position[:, :X.shape[1] ,:]
        return X


class Embedding(nn.Module):
    n_embed: int
    hidden: int
    dropout: float
    max_len: int = 1000

    def setup(self) -> None:
        self.position = PositionEmbedding(hidden=self.hidden, max_len=self.max_len)
        self.embed = nn.Embed(num_embeddings=self.n_embed, features=self.hidden)

    @nn.compact
    def __call__(self, x: jnp.ndarray, training: bool = False) -> jnp.ndarray:
        h = self.embed(x) 
        h = h + self.position(h)
        return nn.Dropout(self.dropout)(h, deterministic=not training)
    

class TransformerBlock(nn.Module):
    hidden: int
    num_heads: int
    dropout: float

    @nn.compact
    def __call__(self, x: jnp.ndarray, training: bool = False) -> jnp.ndarray:
        h = nn.MultiHeadAttention(
            num_heads=self.num_heads,
            dropout_rate=self.dropout,
            out_features=self.hidden,
            deterministic=not training
        )(inputs_q=x)

        h = nn.LayerNorm()(h)

        h = nn.gelu(nn.Dense(self.hidden * 2)(h))
        h = nn.Dropout(self.dropout)(h, deterministic=not training)
        h = nn.Dense(self.hidden)(h)

        return h + x


class LogBertModel(nn.Module):
    n_embed: int
    hidden: int
    num_heads: int
    n_layers: int
    dropout: float
    max_len: int = 1000

    def setup(self) -> None:
        self.special_tokens = 2

    @nn.compact
    def __call__(self, x: jnp.ndarray, training: bool = False) -> tuple[jnp.ndarray, jnp.ndarray]:
        x = jnp.concat([x, jnp.ones((x.shape[0], 1), dtype=jnp.int32)], axis=1)
        h = Embedding(
            n_embed=self.n_embed + self.special_tokens, hidden=self.hidden, dropout=self.dropout
        )(x + self.special_tokens)

        for _ in range(self.n_layers):
            h = TransformerBlock(
                hidden=self.hidden, num_heads=self.num_heads, dropout=self.dropout
            )(h, training=training)      
        h, dist = h[:, :-1, :], h[:, -1, :]

        return nn.Dense(self.n_embed)(h), dist


@dataclass
class TrainConfig:
    seed: int = 0
    epochs: int = 40
    learning_rate: float = 0.01
    batch_size: int = 2
    mask_per: float = 0.4
    alpha: float = 0.0
    patience: int = 3


def loss_(
    model: nn.Module, params: dict[str, Any], x: jnp.ndarray, m: jnp.ndarray, alpha: float
) -> jnp.ndarray:
    
    logist, h_dist = model.apply({"params": params}, x * m, training=True)
    loss_mlkp = ((1 - m) * optax.softmax_cross_entropy_with_integer_labels(
        logits=logist, labels=x
    ))
    loss_vhm = jnp.linalg.norm(h_dist - h_dist.mean(axis=1)[..., None], axis=1) ** 2

    return loss_mlkp.mean() + alpha * loss_vhm.mean()


def train(
    model: nn.Module, x: jnp.ndarray, x_val: jnp.ndarray, mask: Mask, trainConfig=TrainConfig()
) -> tuple[dict[str, Any], dict[str, float]]:
    @jax.jit
    def train_step(params, opt_state, x, m, alpha):
        def loss_f(params):
            return loss_(model=model, params=params, x=x, m=m, alpha=alpha)
        
        loss, grads = jax.value_and_grad(loss_f)(params)
        updates, opt_state = optimizer.update(grads, opt_state)
        params = optax.apply_updates(params, updates)
        return params, opt_state, loss
    
    seed = jax.random.key(trainConfig.seed)
    n_steps = ceil(x.shape[0] / trainConfig.batch_size)

    params = model.init(seed, jnp.zeros((1, x.shape[-1]), dtype=jnp.int32))["params"]
    optimizer = optax.adam(learning_rate=trainConfig.learning_rate)
    opt_state = optimizer.init(params)

    idx = jnp.arange(x.shape[0])
    idx = jax.random.permutation(jax.random.key(trainConfig.seed), idx)

    losses_epoch, losses_step, loss_val =  [], [], []
    checkpoint, alpha = CheckPoint(TrainConfig.patience), trainConfig.alpha
    for epoch in tqdm(range(trainConfig.epochs), desc="training..."):
        step_loss = 0
        for step_idx in jnp.array_split(idx, n_steps):
            x_step = x[step_idx]
            m = mask(x_step.shape[0])
            params, opt_state, loss = train_step(params, opt_state, x_step, m, alpha=alpha)
            step_loss += loss
            losses_step.append(loss)

        m = mask(x_val.shape[0])
        loss_val.append(loss_(model=model, params=params, x=x_val, m=m, alpha=alpha))
        losses_epoch.append(step_loss / n_steps)
        idx = jax.random.permutation(jax.random.key(epoch), idx)
        if checkpoint(loss=loss_val[-1], epoch=epoch, param=params):
            logging.info("Early stop")
            break

    best_e, params = checkpoint.load_checkpoint()
    logging.info(f"Best epoch {best_e} -> Train {losses_epoch[best_e]} Val {loss_val[best_e]}")
    return params, {
        "Loss Epoch": losses_epoch, "Loss Step": losses_step, "Loss Val": loss_val, "Best val": loss_val[best_e]
    }


## Final model
default_config = {
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
}


class LogBert(DeepModel):
    def __init__(self, config: dict = default_config) -> None:
        self.config = config
        self.params = {}
        self.model: LogBertModel | None = None
        self.mask: Mask | None = None
        self.config_train = TrainConfig(**self.config["Train"])

    def __str__(self) -> str:
        return str(self.model) + "\n" + str(self.config_train)
    
    def top_pred(self, x: jnp.ndarray) -> tuple[jnp.ndarray]:
        m = self.mask(x.shape[0])
        y, _ = self.model.apply({"params": self.params}, x * m, training=False)

        idx = jnp.nonzero(m == 0)
        pred = jnp.argsort(y[idx], axis=1, descending=True)
        return pred, x[idx]

    def get_best_k(self, seq: jnp.ndarray) -> int:
        if seq.shape[0] == 0:
            return 0

        pred, y = self.top_pred(seq)
        return int(jax.scipy.stats.mode(
            ((y[..., None] == pred) * jnp.arange(pred.shape[1])[None, ...]).sum(1)
        ).mode + 2)

    @lru_cache
    def check_anomaly(self, seq: tuple[int], top_k: int) -> int:
        if self.model is None:
            return False
        
        pred, y = self.top_pred(jnp.array([seq]))
        pred = pred[:, :top_k]
        score = 0
        for i in range(pred.shape[0]):
            score += not bool(jnp.isin(y[i], pred[i]))
        return score

    def _prepare_data(self, seqs: list[tuple[int]], var_per: float) -> tuple[jnp.ndarray]:
        seed = jax.random.key(self.config_train.seed)
        idx = jax.random.permutation(seed, len(seqs))
        seqs = jnp.array(seqs)[idx]
        train_seqs = seqs[:ceil(len(seqs) * (1 - var_per))]
        val_seqs = seqs[ceil(len(seqs) * (1 - var_per)):]
        return train_seqs, val_seqs

    def train(self, seqs: list[tuple[int]], var_per: float) -> dict[str, int | float]:
        train_seqs, val_seqs = self._prepare_data(seqs=seqs, var_per=var_per)

        self.config_train = TrainConfig(**self.config["Train"])
        self.config["Model"]["n_embed"] = int(train_seqs.max() + 1)
        self.model = LogBertModel(**self.config["Model"])
        self.mask = Mask(
            seq_size=train_seqs.shape[-1], mask_per=self.config_train.mask_per
        )
        self.params, stats = train(
            model=self.model, mask=self.mask, x=train_seqs, x_val=val_seqs, trainConfig=self.config_train
        ) 
        stats["top_k"] = self.get_best_k(val_seqs)

        return stats
    
    def finetune(self, seqs: list[tuple[int]], var_per: float, epochs: int = 2) -> None:
        train_seqs, val_seqs = self._prepare_data(seqs=seqs, var_per=var_per)
        combos = Combinations(config=self.config)

        for comb in combos():
            comb["Model"]["n_embed"] = int(train_seqs.max() + 1)
            comb["Train"]["epochs"] = epochs
            model = LogBertModel(**comb["Model"])
            config_train = TrainConfig(**comb["Train"])
            mask = Mask(
                seq_size=train_seqs.shape[-1], mask_per=config_train.mask_per
            )

            _, stats = train(
                model=model, mask=mask, x=train_seqs, x_val=val_seqs, trainConfig=config_train
            )
            combos.add_value(stats["Best val"])
        self.config = combos.get_best()
        logging.info(self.config)
        