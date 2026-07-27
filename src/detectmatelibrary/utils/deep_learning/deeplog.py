import jax.numpy as jnp
import jax

import flax.linen as nn
import optax

from functools import lru_cache

from dataclasses import dataclass
from typing import Any
from tqdm import tqdm
from math import ceil

from detectmatelibrary.utils.deep_learning.imodel import DeepModel
from detectmatelibrary.utils.deep_learning._op import CheckPoint
from detectmatelibrary.utils.finetune import Combinations

import logging


## Model Deeplog
class DeepLogModel(nn.Module):
    hidden_dim: int
    n_layers: int
    output_size: int = 1
    
    @nn.compact
    def __call__(self, x: jnp.ndarray) -> jnp.ndarray:        
        for _ in range(self.n_layers):
            lstm_cell = nn.OptimizedLSTMCell(features=self.hidden_dim)
            x = nn.RNN(lstm_cell)(x)
        
        last_step = x[:, -1, :]
        return nn.Dense(features=self.output_size)(last_step)


## Train script
@dataclass
class TrainConfig:
    seed: int = 0
    epochs: int = 40
    learning_rate: float = 0.05
    batch_size: int = 2
    patience: int = 3


def loss_f(model: nn.Module, params: dict[str, Any], x: jnp.ndarray, y: jnp.ndarray) -> jnp.ndarray:
    return optax.softmax_cross_entropy_with_integer_labels(
            logits=model.apply({'params': params}, x), labels=y
        ).mean()


def train(
    model: nn.Module, 
    x: jnp.ndarray, 
    y: jnp.ndarray, 
    x_val: jnp.ndarray, 
    y_val: jnp.ndarray, 
    trainConfig: TrainConfig = TrainConfig()
) -> tuple[dict[str, Any], dict[str, float]]:
    @jax.jit
    def train_step(
        params: dict[str, Any], opt_state: optax.OptState, x: jnp.ndarray, y: jnp.ndarray
    ) -> jnp.ndarray:
        def loss_fn(params: dict[str, Any]) -> jnp.ndarray:
            return loss_f(params=params, x=x, y=y, model=model)
        
        loss, grads = jax.value_and_grad(loss_fn)(params)
        updates, opt_state = optimizer.update(grads, opt_state)
        params = optax.apply_updates(params, updates)
        return params, opt_state, loss
        
    key = jax.random.PRNGKey(trainConfig.seed)
    n_steps = ceil(x.shape[0] / trainConfig.batch_size)

    variables = model.init(key, x[:1])
    params = variables['params']
    optimizer = optax.adam(learning_rate=trainConfig.learning_rate)
    opt_state = optimizer.init(params)

    idx = jnp.arange(x.shape[0])
    idx = jax.random.permutation(jax.random.key(trainConfig.seed), idx)
    
    losses_epoch, losses_step, loss_val =  [], [], []
    checkpoint = CheckPoint(trainConfig.patience)
    for epoch in tqdm(range(trainConfig.epochs), desc="training..."):
        step_loss = 0
        for step_idx in jnp.array_split(idx, n_steps):
            params, opt_state, loss = train_step(
                params, opt_state, x[step_idx], y[step_idx]
            )
            step_loss += loss
            losses_step.append(loss)
        losses_epoch.append(step_loss / n_steps)
        loss_val.append(loss_f(model=model, params=params, x=x_val, y=y_val))
        idx = jax.random.permutation(jax.random.key(epoch), idx)
        if checkpoint(loss=loss_val[-1], epoch=epoch, param=params):
            logging.info("Early stop")
            break
    
    best_e, params = checkpoint.load_checkpoint()
    logging.info(f"Best epoch {best_e} -> Train {losses_epoch[best_e]} Val {loss_val[best_e]}")
    return params, {
        "Loss Epoch": losses_epoch, 
        "Loss Step": losses_step, 
        "Loss Val": loss_val, 
        "Best val": loss_val[best_e]
    }


def do_train(
    model: nn.Module, train_seqs: jnp.ndarray, val_seqs: jnp.ndarray, config: TrainConfig
) -> tuple[dict[str, Any], dict[str, float]]:
    return train(
        model=model, 
        x=train_seqs[:, :-1, :], 
        y=train_seqs[:, -1, :].reshape((train_seqs.shape[0])), 
        x_val=val_seqs[:, :-1, :], 
        y_val=val_seqs[:, -1, :].reshape((val_seqs.shape[0])), 
        trainConfig=config
    ) 


## Final model
default_config = {
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
}


class DeepLog(DeepModel):
    def __init__(self, config: dict = default_config) -> None:
        self.config = config
        self.params = {}
        self.config_train = TrainConfig(**config["Train"])
        self.model_trained = False
        self.model: DeepLogModel | None = None

    def __str__(self) -> str:
        return str(self.model) + "\n" + str(self.config_train)

    def top_pred(self, x: jnp.ndarray) -> jnp.ndarray:
        return jnp.argsort(
            self.model.apply({"params": self.params}, x[None, ..., None]).flatten(),
            descending=True
        )
    
    def get_best_k(self, seq: jnp.ndarray) -> int:
        if seq.shape[0] == 0:
            return 0

        x_s, y_s = seq[:, :-1, :], seq[:, -1]
        x_s = jnp.argsort(
            self.model.apply({"params": self.params}, x_s), descending=True
        )

        return int(jax.scipy.stats.mode(
            (jnp.arange(x_s.shape[1]) * (x_s == y_s)).sum(1)
        ).mode + 2)  # give a little space for variation

    @lru_cache
    def check_anomaly(self, seq: tuple[int], top_k: int) -> bool:
        if not self.model_trained:
            return False

        seq = jnp.array(seq)
        x, y = seq[:-1], seq[-1]
        return not jnp.isin(y, self.top_pred(x)[:top_k])

    def _prepare_data(self, seqs: list[tuple[int]], var_per: float) -> tuple[jnp.ndarray]:
        seed = jax.random.key(self.config_train.seed)
        idx = jax.random.permutation(seed, len(seqs))
        seqs = jnp.array(seqs)[..., None][idx]
        train_seqs = seqs[:ceil(len(seqs) * (1 - var_per))]
        val_seqs = seqs[ceil(len(seqs) * (1 - var_per)):]
        return train_seqs, val_seqs

    def train(self, seqs: list[tuple[int]], var_per: float) -> dict[str, int | float]:
        train_seqs, val_seqs = self._prepare_data(seqs=seqs, var_per=var_per)

        self.config_train = TrainConfig(**self.config["Train"])
        self.config["Model"]["output_size"] = train_seqs.max() + 1
        logging.info(f"Output shape: {self.config["Model"]["output_size"]}")

        self.model = DeepLogModel(**self.config["Model"])
        self.params, stats = do_train(
            self.model, train_seqs=train_seqs, val_seqs=val_seqs, config=self.config_train
        ) 
        self.model_trained = True
        stats["top_k"] = self.get_best_k(val_seqs)

        return stats
 
    def finetune(self, seqs: list[tuple[int]], var_per: float, epochs: int = 2) -> None:
        train_seqs, val_seqs = self._prepare_data(seqs=seqs, var_per=var_per)
        combos = Combinations(config=self.config)

        for comb in combos():
            comb["Model"]["output_size"] = train_seqs.max() + 1
            comb["Train"]["epochs"] = epochs
            model = DeepLogModel(**comb["Model"])
            config_train = TrainConfig(**comb["Train"])

            _, stats = do_train(model, train_seqs=train_seqs, val_seqs=val_seqs, config=config_train) 
            combos.add_value(stats["Best val"])
        self.config = combos.get_best()
        logging.info(self.config)