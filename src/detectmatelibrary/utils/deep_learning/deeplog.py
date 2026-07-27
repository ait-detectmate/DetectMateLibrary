import jax.numpy as jnp
import jax

import flax.linen as nn
import optax

from dataclasses import dataclass
from typing import Any
from tqdm import tqdm
from math import ceil

from detectmatelibrary.utils.deep_learning._op import CheckPoint


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
):
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
            print("Early stop")
            break
    
    best_e, params = checkpoint.load_checkpoint()
    print(f"Best epoch {best_e} -> Train {losses_epoch[best_e]} Val {loss_val[best_e]}")
    return params, {
        "Loss Epoch": losses_epoch, 
        "Loss Step": losses_step, 
        "Loss Val": loss_val, 
        "Best val": loss_val[best_e]
    }