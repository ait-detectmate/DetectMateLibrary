# ty: ignore[invalid-mutable-override] # Used to silence an error in the typing of nn.ModuleDict!

from __future__ import annotations

import json
import logging
import os
from collections import OrderedDict
from collections.abc import Callable, Sequence
from datetime import datetime as dt
from math import ceil, floor
from typing import TYPE_CHECKING, Any, Literal, cast

import numpy as np
import torch
from alertbert.datasets import AlertDataset, AlertSequenceBatchSampler
from alertbert.preprocessing import (
    BaseSequenceCollate,
    MaskedLangModelingSequenceCollate,
    Vocabulary,
    default_collate_fn,
)
from scipy.sparse import coo_array
from scipy.sparse.csgraph import connected_components
from sklearn.decomposition import PCA
from sklearn.metrics import f1_score, matthews_corrcoef, precision_score, recall_score
from sklearn.metrics.pairwise import cosine_distances
from tensordict import TensorDict
from tensordict.nn import TensorDictModule
from torch import nn
from torch.utils.data import DataLoader

from detectmatelibrary.schemas import DetectorSchema
from detectmatelibrary.tools.logging import setup_logging

if TYPE_CHECKING:
    from detectmatelibrary.alert_aggregation.alertbert import (
        AlertBERTAggregationConfig,
    )

# region model components


class MaskedLangModelEmbeddingLayer(nn.Module):
    """A module that represents the embedding layer for a masked language
    model.

    Args:
        features (list[str]): List of feature to use.
        encoding (str | None): Feature to use for positional encoding.
        vocabs (dict[str, Vocabulary]): Dictionary of feature vocabularies.
        dim (int): Dimension of the embeddings.
        init_std (float, optional): Standard deviation of the normal distribution used
            for initializing the embeddings. Defaults to 1.0.
        context_size (int, optional): Size of the context for positional encoding.
            Defaults to None.

    Attributes:
        dim (int): Dimension of the embeddings.
        features (list[str]): List of feature names.
        n_features (int): Number of features.
        encoding (str | None): Feature to use for positional encoding.
        vocabs (dict[str, Vocabulary]): Dictionary of feature vocabularies.
        embeddings (nn.ModuleDict): Module dictionary of feature embeddings.

    Methods:
        forward(**src: torch.Tensor) -> torch.Tensor:
            Forward pass of the module.
    """

    def __init__(
        self,
        features: list[str],
        encoding: str | None,
        vocabs: dict[str, Vocabulary],
        dim: int,
        context_size: int,
        init_std: float = 1.0,
    ) -> None:
        super().__init__()
        self.dim = dim
        self.features = list(features)
        self.n_features = len(features)
        self.encoding = encoding
        self.vocabs = vocabs
        self.layernorm: Callable[[torch.Tensor], torch.Tensor] = nn.LayerNorm(dim)
        self.embeddings = nn.ModuleDict(
            {
                f: nn.Embedding(
                    num_embeddings=vocabs[f].vocab_size,
                    embedding_dim=dim,
                    max_norm=None,
                    norm_type=2.0,
                )
                for f in features
            }
        )
        for emb in self.embeddings.values():
            emb.weight = nn.init.normal_(torch.tensor(emb.weight), mean=0, std=init_std)

        if self.encoding == "position":
            self.embeddings["position"] = nn.Embedding(
                num_embeddings=context_size, embedding_dim=dim
            )
        elif self.encoding == "raw_time":
            raise NotImplementedError("Learned time encoding is not supported")

    def forward(self, **src: torch.Tensor) -> torch.Tensor:
        x = [self.embeddings[k](src[k]) for k in self.embeddings]
        y = torch.sum(torch.stack(x), dim=0)
        return self.layernorm(y)


class RotaryEmbedding(nn.Module):
    """A module that represents the rotary positional encoding for a masked
    language model.

    Args:
        dim (int): Dimension of the embeddings.
        freqs (list[float]): List of frequencies to use for the positional encoding.

    Attributes:
        dim (int): Dimension of the embeddings.
        freqs (torch.Tensor): Tensor of frequencies to use for the positional encoding.

    Methods:
        forward(q: torch.Tensor, k: torch.Tensor, p: torch.Tensor) -> tuple[torch.Tensor]:
            Forward pass of the module.
    """

    def __init__(self, dim: int, freqs: list[float]) -> None:
        super().__init__()
        self.dim = dim
        if not len(freqs) <= dim // 2:
            raise ValueError(
                "Number of frequencies must be less than or equal to dim // 2"
            )
        if len(freqs) < dim // 2:
            freqs = freqs + [0.0] * (dim // 2 - len(freqs))
        freqs2 = torch.tensor(freqs, dtype=torch.float64)
        self.freqs = nn.Parameter(
            torch.cat([freqs2, -freqs2], dim=0), requires_grad=False
        )

    @torch.no_grad()
    def _get_rotation(
        self, position_ids: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns the rotation matrices for the given position ids."""
        if not position_ids.dtype == torch.float32:
            raise ValueError("position_ids must be of type torch.float32")
        position_ids = position_ids.to(torch.float64)
        # position_ids: [batch_size, seqlen]
        # freqs: [head_dim]
        # cos, sin: [batch_size, seq_len, head_dim]
        cos = (
            torch.cos(position_ids.unsqueeze(-1) * self.freqs)
            .requires_grad_(False)
            .to(torch.float32)
        )
        sin = (
            torch.sin(position_ids.unsqueeze(-1) * self.freqs)
            .requires_grad_(False)
            .to(torch.float32)
        )
        return cos, sin

    def _rotate_half(self, x: torch.Tensor) -> torch.Tensor:
        """Rotates half the hidden dims of the input."""
        x1, x2 = torch.chunk(x, 2, dim=-1)
        return torch.cat((x2, x1), dim=-1)

    def forward(
        self, q: torch.Tensor, k: torch.Tensor, p: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        cos, sin = self._get_rotation(p)
        # q, k: [batch_size, heads, seq_len, head_dim]
        # cos, sin: [batch_size, seq_len, head_dim]
        cos = cos.unsqueeze(1)
        sin = sin.unsqueeze(1)
        q = q * cos + self._rotate_half(q) * sin
        k = k * cos + self._rotate_half(k) * sin
        return q, k


class SelfAttention(nn.Module):
    """A module that represents the self-attention mechanism for a masked
    language model.

    Args:
        d_model (int): Dimension of the embeddings.
        nhead (int): Number of attention heads.
        rotary_pos_enc (bool, optional): Whether to use rotary positional encoding. Defaults to False.
        rotary_pos_enc_freqs (list[float], optional): List of frequencies to use for the positional encoding.
            Defaults to None.
        biases (bool, optional): Whether to use biases in the linear layers. Defaults to True.

    Attributes:
        nhead (int): Number of attention heads.
        d_model (int): Dimension of the embeddings.
        dim_head (int): Dimension of the embeddings per head.
        scale (float): Scaling factor for the attention weights.
        rotary_pos_enc (bool): Whether to use rotary positional encoding.

    Methods:
        forward(x: torch.Tensor, p: torch.Tensor = None, return_attn_weights: bool = False) -> torch.Tensor:
            Forward pass of the module.
            If rotary_pos_enc is set to True, the parameter p is used for rotary positional encoding.
            If return_attn_weights is set to True, the attention weights are returned instead of the output.
    """

    def __init__(
        self,
        d_model: int,
        nhead: int,
        rotary_pos_enc: bool = False,
        rotary_pos_enc_freqs: Sequence[float] | None = None,
        biases: bool = True,
    ) -> None:
        super().__init__()
        self.Wqkv = nn.Linear(d_model, d_model * 3, bias=biases)
        self.Wo = nn.Linear(d_model, d_model, bias=biases)
        self.nhead = nhead
        self.d_model = d_model
        self.dim_head = d_model // nhead
        self.scale = self.dim_head**-0.5
        self.rotary_pos_enc = rotary_pos_enc
        if rotary_pos_enc:
            if rotary_pos_enc_freqs is None:
                raise ValueError(
                    "rotary_pos_enc_freqs must be provided if rotary_pos_enc is True"
                )
            freqs = list(rotary_pos_enc_freqs)
            self.rotary_emb = RotaryEmbedding(
                dim=self.dim_head, freqs=freqs
            )
        self.softmax = nn.Softmax(dim=-1)

    def forward(
        self, x: torch.Tensor, p: torch.Tensor | None = None, return_attn_weights: bool = False
    ) -> torch.Tensor:
        # qkv: [batch_size, seqlen, 3, nheads, headdim]
        qkv = self.Wqkv(x).view(x.size(0), x.size(1), 3, self.nhead, self.dim_head)

        # query, key, value: [batch_size, heads, seq_len, head_dim]
        query, key, value = qkv.transpose(3, 1).unbind(dim=2)
        if self.rotary_pos_enc:
            query, key = self.rotary_emb(query, key, p)

        attn_weights: torch.Tensor = torch.matmul(query, key.transpose(2, 3)) * self.scale
        attn_weights = self.softmax(attn_weights)
        if return_attn_weights:
            return attn_weights

        attn_output: torch.Tensor = torch.matmul(attn_weights, value)
        attn_output = attn_output.transpose(1, 2).contiguous()
        out: torch.Tensor = attn_output.view(x.size(0), x.size(1), self.d_model)
        out2: torch.Tensor = self.Wo(out)
        return out2


class EncoderMLP(nn.Module):
    """A module that represents the multi-layer perceptron for a masked
    language model.

    Args:
        d_model (int): Dimension of the embeddings.
        dim_feedforward (int): Dimension of the feedforward network.
        activation (Literal["relu", "gelu"], optional): The activation function to be used.
            Defaults to "gelu".
        gated_activation (bool, optional): Whether to use gated activation. Defaults to True.
        biases (bool, optional): Whether to use biases in the linear layers. Defaults to True.

    Methods:
        forward(x: torch.Tensor) -> torch.Tensor: Forward pass of the module.
    """

    def __init__(
        self,
        d_model: int,
        dim_feedforward: int,
        activation: Literal["relu", "gelu"] = "gelu",
        gated_activation: bool = True,
        biases: bool = True,
    ) -> None:
        super().__init__()
        if gated_activation:
            self.linear1 = nn.Linear(d_model, dim_feedforward * 2, bias=biases)
        else:
            self.linear1 = nn.Linear(d_model, dim_feedforward, bias=biases)
        self.linear2 = nn.Linear(dim_feedforward, d_model, bias=biases)
        self.activation = nn.GELU() if activation == "gelu" else nn.ReLU()
        self.gated_activation = gated_activation
        self.dropout = nn.Dropout(0.1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.linear1(x)
        if self.gated_activation:
            x, gate = torch.chunk(x, 2, dim=-1)
            x = self.activation(x) * gate
        else:
            x = self.activation(x)
        x = self.dropout(x)
        x = self.linear2(x)
        return x


class EncoderLayer(nn.Module):
    """A module that represents an encoder layer in a masked language model.

    Args:
        d_model (int): Dimension of the embeddings.
        nhead (int): Number of attention heads.
        dim_feedforward (int): Dimension of the feedforward network.
        activation (Literal["relu", "gelu"], optional): The activation function to be used.
            Defaults to "gelu".
        gated_activation (bool, optional): Whether to use gated activation. Defaults to True.
        rotary_pos_enc (bool, optional): Whether to use rotary positional encoding. Defaults to False.
        rotary_pos_enc_freqs (list[float], optional): List of frequencies to use for the positional encoding.
            Defaults to None.
        biases (bool, optional): Whether to use biases in the linear layers. Defaults to True.

    Methods:
        forward(x: torch.Tensor, p: torch.Tensor = None) -> torch.Tensor: Forward pass of the module.
    """

    def __init__(
        self,
        d_model: int,
        nhead: int,
        dim_feedforward: int,
        activation: Literal["relu", "gelu"] = "gelu",
        gated_activation: bool = True,
        rotary_pos_enc: bool = False,
        rotary_pos_enc_freqs: Sequence[float] | None = None,
        biases: bool = True,
    ) -> None:
        super().__init__()
        self.self_attn = SelfAttention(
            d_model=d_model,
            nhead=nhead,
            rotary_pos_enc=rotary_pos_enc,
            rotary_pos_enc_freqs=rotary_pos_enc_freqs,
            biases=biases,
        )
        self.attn_norm = nn.LayerNorm(normalized_shape=d_model, bias=biases)
        self.mlp = EncoderMLP(
            d_model=d_model,
            dim_feedforward=dim_feedforward,
            activation=activation,
            gated_activation=gated_activation,
            biases=biases,
        )
        self.mlp_norm = nn.LayerNorm(normalized_shape=d_model, bias=biases)

    def forward(self, x: torch.Tensor, p: torch.Tensor | None = None) -> torch.Tensor:
        out = self.attn_norm(self.self_attn(x, p) + x)
        out2: torch.Tensor = self.mlp_norm(self.mlp(out) + out)
        return out2


class MaskedLangModelEncoder(nn.Module):
    """A module that represents the encoder for a masked language model.

    Args:
        d_model (int): Dimension of the embeddings.
        nhead (int): Number of attention heads.
        num_layers (int): Number of encoder layers.
        dim_feedforward (int): Dimension of the feedforward network.
        activation (Literal["relu", "gelu"], optional): The activation function to be used.
            Defaults to "gelu".
        gated_activation (bool, optional): Whether to use gated activation. Defaults to True.
        rotary_pos_enc (bool, optional): Whether to use rotary positional encoding. Defaults to False.
        rotary_pos_enc_freqs (list[float], optional): List of frequencies to use for the positional encoding.
            Defaults to None.
        biases (bool, optional): Whether to use biases in the linear layers. Defaults to True.

    Methods:
        forward(x: torch.Tensor, p: torch.Tensor = None) -> torch.Tensor: Forward pass of the module.
    """

    def __init__(
        self,
        d_model: int,
        nhead: int,
        num_layers: int,
        dim_feedforward: int,
        activation: Literal["relu", "gelu"] = "gelu",
        gated_activation: bool = True,
        rotary_pos_enc: bool = False,
        rotary_pos_enc_freqs: Sequence[float] | None = None,
        biases: bool = True,
    ) -> None:
        super().__init__()
        self.layers: nn.ModuleList = nn.modules.transformer._get_clones(  # type: ignore[no-untyped-call]
            EncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=dim_feedforward,
                activation=activation,
                gated_activation=gated_activation,
                rotary_pos_enc=rotary_pos_enc,
                rotary_pos_enc_freqs=rotary_pos_enc_freqs,
                biases=biases,
            ),
            num_layers,
        )

    def forward(self, x: torch.Tensor, p: torch.Tensor | None = None) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x, p)
        return x


class MultiClassificationHead(nn.Module):
    """Module that represents the classification head for a multi-
    classification task.

    Args:
        d_model (int): The input dimension of the head.
        targets (list[str]): The list of target names.
        vocabs (dict[str, Vocabulary]): The dictionary of target names and their corresponding
            Vocabulary objects.
        bias (bool, optional): Whether to use biases in the linear layers. Defaults to True.

    Attributes:
        targets (list[str]): The list of target names.
        vocabs (dict[str, Vocabulary]): The dictionary of target names and their corresponding
            Vocabulary objects.
        linear (nn.ModuleList): List of linear layers for each target.

    Methods:
        forward(x: torch.Tensor) -> tuple[torch.Tensor]: Forward pass of the module.
    """

    def __init__(
        self,
        d_model: int,
        targets: list[str],
        vocabs: dict[str, Vocabulary],
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.targets = targets
        self.vocabs = vocabs
        self.d_model = d_model
        self.linear = nn.ModuleDict(
            {
                t: nn.Linear(d_model, self.vocabs[t].vocab_size, bias=bias)
                for t in self.targets
            }
        )
        # set all biases to zero
        if bias:
            for linear in self.linear.values():
                nn.init.zeros_(cast(nn.Linear, linear).bias)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor]:
        return tuple(
            self.linear[t](x)[..., self.vocabs[t].offset:] for t in self.targets
        )


class MultiTargetLoss(nn.Module):
    """A module that combines multiple loss functions for multi-target
    learning.

    Args:
        loss_fns (list[nn.Module]): A list of loss functions to be combined.

    Methods:
        forward(output: tuple[torch.tensor], target: tuple[torch.tensor]) -> torch.tensor:
            Forward pass of the module.
    """

    def __init__(self, loss_fns: list[nn.Module]) -> None:
        super().__init__()
        self.loss_fns = nn.ModuleList(loss_fns)

    def forward(
        self, output: tuple[torch.Tensor], target: tuple[torch.Tensor]
    ) -> torch.Tensor:
        return torch.mean(
            torch.stack(
                tuple(
                    loss_fn(out, tar)
                    for loss_fn, out, tar in zip(self.loss_fns, output, target)
                )
            )
        )


@torch.compile
class MaskedLanguageModel(nn.ModuleDict):
    """Module that represents a masked language model.

    Args:
        config (AlertBERTAggregationConfig): Configuration of model parameters, for more information
            see the documentation of `detectmatelibrary.alert_aggrgation.AlertBertAggregationConfig`.

    Attributes:
        config (AlertBERTAggregationConfig): Configuration of model parameters.
        path (str): Path to the model.
        device (torch.device): Device on which the model is running.
        vocabs (dict[str, Vocabulary]): Dictionary of feature vocabularies.

    Methods:
        forward(**src: dict[str,torch.Tensor]) -> tuple[torch.Tensor]: Forward pass of the module.
        fit(train_data: AlertDataset, val_data: AlertDataset) -> None: Trains the model on the given
            training and validation datasets.
    """

    def __init__(
        self,
        config: AlertBERTAggregationConfig,
    ) -> None:
        self.config = config._get_mlm_config()
        self.path = f"{self.config['path']}/{self.config['model_id']}"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.config["d_model"] = self.config["n_heads"] * self.config["dim_per_head"]
        self.config["dim_feedforward"] = (
            self.config["n_heads"]
            * self.config["dim_per_head"]
            * self.config["feedforward_factor"]
        )
        self.config["emb_init_std"] = (
            self.config["n_heads"] * self.config["dim_per_head"]
        ) ** -0.5
        self.config["rotary_pos_enc_freqs"] = list(
            2
            ** (
                np.array(
                    range(
                        int(
                            self.config["dim_per_head"]
                            // 2.0
                            * self.config["rotary_cutoff"]
                        )
                    )
                )
                * -2.0
                / self.config["dim_per_head"]
                * self.config["rotary_max_exp"]
            )
        )
        self.config["tag"] = (
            f"{self.config['method_type']}_{self.config['num_layers']}l_\
            {self.config['n_heads']}h_{self.config['dim_per_head']}d"
        )

        if not self.config["train_model"]:
            self._load_model()
            self._set_up_model()
        else:
            os.makedirs(
                f"{self.config['path']}/{self.config['model_id']}", exist_ok=True
            )

    def _set_up_model(self) -> None:
        super().__init__(
            {
                "embedding": MaskedLangModelEmbeddingLayer(
                    features=self.config["features"],
                    encoding=None,
                    vocabs=self.vocabs,
                    dim=self.config["d_model"],
                    init_std=self.config["emb_init_std"],
                    context_size=self.config["context_size"],
                ),
                "encoder": MaskedLangModelEncoder(
                    d_model=self.config["d_model"],
                    nhead=self.config["n_heads"],
                    num_layers=self.config["num_layers"],
                    dim_feedforward=self.config["dim_feedforward"],
                    rotary_pos_enc_freqs=self.config["rotary_pos_enc_freqs"],
                ),
                "head": MultiClassificationHead(
                    d_model=self.config["d_model"],
                    targets=self.config["features"],
                    vocabs=self.vocabs,
                ),
            }
        )
        # tie weigths of the embedding layer and the output layer
        for t in self.config["features"]:
            head = cast(MultiClassificationHead, self["head"])
            embedding = cast(MaskedLangModelEmbeddingLayer, self["embedding"])
            head.linear[t].weight = embedding.embeddings[t].weight

        self.to(self.device)

    def forward(self, **src: torch.Tensor) -> tuple[torch.Tensor]:
        embedding = cast(MaskedLangModelEmbeddingLayer, self["embedding"])
        encoder = cast(MaskedLangModelEncoder, self["encoder"])
        head = cast(MultiClassificationHead, self["head"])
        x: torch.Tensor = embedding(**src)
        x = encoder(x, p=src[self.config["encoding"]])
        return cast(tuple[torch.Tensor], head(x))

    def fit(self, train_data: AlertDataset, val_data: AlertDataset) -> None:
        # set up environment

        os.makedirs(self.path, exist_ok=True)
        logfile = f"{self.path}/training.log"
        setup_logging(logfile=logfile)
        logging.info(f"Run id: {self.config['tag']}")
        logging.info(f"Using device: {self.device}")

        # load data

        self._build_feature_vocabs(
            dataset=train_data,
            features=list(set(self.config["features"])),
            min_freq=self.config["min_freq"],
        )
        self.vocabs[self.config["encoding"]] = default_collate_fn

        self.collate_function = MaskedLangModelingSequenceCollate(
            self.vocabs,
            0.2,
            0.8,
            0.0,
        )

        train_sampler = AlertSequenceBatchSampler(
            train_data,
            context_size=self.config["context_size"],
            batch_size=self.config["batch_size"],
        )
        val_sampler = AlertSequenceBatchSampler(
            val_data,
            context_size=self.config["context_size"],
            batch_size=self.config["batch_size"],
            drop_last=False,
            shuffle=False,
        )

        train_loader = DataLoader(
            train_data,
            batch_sampler=train_sampler,
            collate_fn=self.collate_function,
        )
        val_loader = DataLoader(
            val_data,
            batch_sampler=val_sampler,
            collate_fn=self.collate_function,
        )

        # build model

        self._set_up_model()
        self.to(self.device)

        # calculate epochs from updates
        save_interval = self.config["updates"]
        save_interval_epochs = (
            floor(save_interval[0] / len(train_loader)),
            ceil(save_interval[1] / len(train_loader)),
        )
        epochs = save_interval_epochs[1]
        updates_per_epoch = len(train_loader)

        save_interval_start, save_interval_end = save_interval_epochs
        saving = False

        logging.info(
            f"Specified number of {self.config['updates'][1]} updates amounts to {epochs} epochs \
                with {updates_per_epoch} updates per epoch."
        )
        logging.info(f"Save intervals in epochs: {save_interval_epochs}")

        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.config["lr"],
            weight_decay=0.1,
            betas=(0.9, 0.999),
        )
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=self.config["lr"],
            total_steps=epochs * updates_per_epoch,
            pct_start=float(self.config["warm_up_steps"])
            / (epochs * updates_per_epoch),
            anneal_strategy="linear",
            cycle_momentum=False,
            div_factor=1e3,
            final_div_factor=1e4,
        )

        class_weights = {
            t: torch.softmax(
                self.vocabs[t].get_frequencies().to(self.device) * -2.0,
                dim=0,
            )
            for t in self.config["features"]
        }

        loss_fn = MultiTargetLoss(
            [
                (torch.nn.CrossEntropyLoss(weight=class_weights[t]))
                for t in self.config["features"]
            ]
        )

        model_tr = MaskedLangModelTrainWrapper(self, loss_fn)

        # train model

        logging.info("Training...")

        for e in range(epochs):
            self.train()

            losses = torch.empty(len(train_loader))
            for i, batch in enumerate(train_loader):
                batch = batch.to(self.device)
                batch = model_tr(batch)
                optimizer.zero_grad()
                batch["loss"].backward()
                optimizer.step()
                scheduler.step()
                losses[i] = batch["loss"].item()
            mean, std = losses.mean(), losses.std()
            if (e < 20) or (e % 10 == 9):
                logging.info(
                    f"Epoch {e + 1:4d}: train loss = {mean:1.05f} ± {std:1.05f}"
                )

            if e + 1 == save_interval_start:
                logging.info("Beginning of save interval.")
                saving = True
                best_val_loss = float("inf")
                best_train_stats = None
                best_val_stats = None

            if saving or (e % 100 == 99):
                # model evaluation every 100 epochs and every epoch during save intervals
                self.eval()

                tr_stats = self._eval_masked_lang_model(train_loader, epochs=3)
                val_stats = self._eval_masked_lang_model(val_loader, epochs=5)
                for t in self.config["features"]:
                    logging.info(
                        f"Evaluation: target = {t}, train loss = {tr_stats[t]['loss']:1.05f}, \
                            train acc = {tr_stats[t]['corr']:1.05f}; val loss = {val_stats[t]['loss']:1.05f}\
                            , val acc = {val_stats[t]['corr']:1.05f}"
                    )

                if saving and val_stats["total_loss"] < best_val_loss:
                    # create a checkpoint for best performing models
                    best_val_loss = val_stats["total_loss"]
                    best_train_stats = tr_stats
                    best_val_stats = val_stats
                    self.config["updates"] = (e + 1) * updates_per_epoch
                    logging.info("Creating checkpoint...")
                    torch.save(self.state_dict(), self.path + "/model.pt")
                    for f in set(self.config["features"]):
                        self.vocabs[f].save(self.path + f"/vocab_{f}.json")
                    self.config["train_model"] = False
                    report = {
                        "model": self.config["model_id"],
                        "timestamp": str(dt.now()),
                        "epochs": e + 1,
                        "training": {
                            t: self._classification_report(tr_stats[t])
                            for t in self.config["features"]
                        },
                        "validation": {
                            t: self._classification_report(val_stats[t])
                            for t in self.config["features"]
                        },
                        "params": self.config,
                    }
                    with open(self.path + "/report.json", "w") as f:
                        json.dump(report, f, indent=4)

        logging.info("End of training.")
        if best_train_stats is None or best_val_stats is None:
            raise RuntimeError("No best model checkpoint was created during training.")
        results = f"{str(dt.now())} Model: {self.config['model_id']} Results: train loss = \
            {best_train_stats['total_loss']:1.05f}, val loss = {best_val_stats['total_loss']:1.05f}"
        for t in self.config["features"]:
            results += f", {t: >5} train acc = {best_train_stats[t]['corr']:1.05f}, \
                {t: >5} val acc = {best_val_stats[t]['corr']:1.05f}"
            results += (
                f", {t: >5} train f1 = {report['training'][t]['macro_f1']:1.05f}, \
                {t: >5} val f1 = {report['validation'][t]['macro_f1']:1.05f}"
            )
        results += f"; params = {self.config}"
        logging.info(results)
        logging.info("Done.")

    def _eval_masked_lang_model(
        self,
        loader: DataLoader[Any],
        epochs: int = 1,
    ) -> dict[str, Any]:
        """Computes evaluation statistics for a masked language model.

        Parameters:
        - model (MaskedLangModelEvalWrapper): The model to evaluate.
        - loader (DataLoader): The data loader.
        - device (torch.device): The device to use for computation.
        - epochs (int): The number of epochs to evaluate.
            As the targets for prediction are randomly chosen every epoch a larger number of
                epochs is recommended for consistent evaluation.

        Returns:
        - dict[str, float | dict[str, torch.tensor]]: A dictionary containing the evaluation statistics.
        """
        model_ev = MaskedLangModelEvalWrapper(self)
        stats: dict[str, Any] = {  # dictionary to store statistics for each target of the model
            t: {
                "loss": [],  # average loss
                "corr": [],  # accuracy
                "rank": [],  # rank of each true label in the prediction
                "pred": [],  # predicted labels
                "true": [],  # true labels
                "size": [],  # number of samples
            }
            for t in model_ev.module["head"].targets
        }
        loss_fn = nn.CrossEntropyLoss(reduction="sum")
        self.eval()
        with torch.no_grad():
            for _ in range(epochs):
                for batch in loader:
                    batch = batch.to(self.device)
                    batch = model_ev(batch)
                    for t in model_ev.module["head"].targets:
                        true = batch[f"{t}_true"]
                        stats[t]["true"].append(true.cpu())
                        stats[t]["size"].append(len(true))
                        out = batch[f"{t}_pred_mask"]
                        loss_value = loss_fn(out, true)
                        stats[t]["loss"].append(loss_value.item())
                        pred = out.argmax(dim=1)
                        stats[t]["pred"].append(pred.cpu())
                        corr = (pred == true).sum()
                        stats[t]["corr"].append(corr.item())
                        rank = torch.sum(
                            out.t() >= out[(torch.arange(len(true)), true)], dim=0
                        )
                        stats[t]["rank"].append(rank.cpu())
        for t in model_ev.module["head"].targets:
            # aggregate statistics
            stats[t]["size"] = sum(stats[t]["size"])
            stats[t]["loss"] = sum(stats[t]["loss"]) / stats[t]["size"]
            stats[t]["corr"] = sum(stats[t]["corr"]) / stats[t]["size"]
            stats[t]["rank"] = torch.cat(stats[t]["rank"])
            stats[t]["pred"] = torch.cat(stats[t]["pred"])
            stats[t]["true"] = torch.cat(stats[t]["true"])
        # add average loss across all targets
        stats["total_loss"] = sum(
            stats[t]["loss"] for t in model_ev.module["head"].targets
        ) / len(model_ev.module["head"].targets)
        return stats

    def _load_report(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load report and param_dict of a saved model."""
        report = json.load(open(f"{self.path}/report.json"))  # noqa: SIM115
        model_param_dict = report["params"]
        return report, model_param_dict

    def _load_model(
        self,
    ) -> None:
        """Loads model from saved state dict."""
        report, model_param_dict = self._load_report()
        for key, value in model_param_dict.items():
            if key in self.config:
                self.config[key] = value
        self._load_feature_vocabs(
            features=self.config["features"], min_freq=self.config["min_freq"]
        )
        self._set_up_model()
        self.load_state_dict(
            torch.load(
                self.path + "/model.pt",
                weights_only=True,
                map_location=self.device,
            ),
        )
        self.eval()

    def _load_feature_vocabs(
        self, features: list[str], min_freq: int = 1
    ) -> None:
        """Load feature vocabularies from the specified path for the given
        features.

        Parameters:
        - path (str): The path from which to load the vocabularies.
        - features (list[str]): The list of features for which to load the vocabularies.
        - min_freq (int): The minimum frequency of a token to be included in the vocabulary.
        """
        self.vocabs = {f: Vocabulary(min_freq=min_freq) for f in features}
        for f in features:
            self.vocabs[f].load(self.path + f"/vocab_{f}.json")

    def _build_feature_vocabs(
        self, dataset: AlertDataset, features: list[str], min_freq: int = 1
    ) -> None:
        """Builds vocabulary dictionaries for the specified features based on
        the given dataset.

        Parameters:
        - dataset (Dataset): The dataset from which to build the vocabularies.
        - features (list[str]): The list of features for which to build the vocabularies.
        - min_freq (int): The minimum frequency of a token to be included in the vocabulary.

        Returns:
        - dict[str, Vocabulary]: A dictionary containing the vocabularies for the specified
        """
        self.vocabs = {f: Vocabulary(min_freq=min_freq) for f in features}
        for f in features:
            self.vocabs[f].build_from_iterator(item[f] for item in dataset)

    def _classification_report(self, stats: dict[str, Any]) -> dict[str, float]:
        """Computes various classification metrics from statistics produced by
        MaskedLanguageModel.eval_masked_lang_model.

        Parameters:
        - stats (dict[str, torch.tensor]): The statistics produced by eval_masked_lang_model.

        Returns:
        - dict[str, float]: A dictionary containing the computed metrics.
        """

        def top_k_accuracy(ranks: torch.IntTensor, k: int) -> float:
            """Calculates the top-k accuracy.

            Parameters:
            - ranks (torch.IntTensor): A tensor containing the ranks of the predictions.
            - k (int): The value of k for top-k accuracy.

            Returns:
            - float: The top-k accuracy.
            """
            return float((ranks <= k).mean(dtype=torch.float64).item())

        y_true = stats["true"]
        y_pred = stats["pred"]
        rank = stats["rank"]
        return {
            "loss": stats["loss"],
            "accuracy": stats["corr"],
            "top_2_accuracy": top_k_accuracy(rank, 2),
            "top_3_accuracy": top_k_accuracy(rank, 3),
            "matthews_corrcoef": matthews_corrcoef(y_true, y_pred),
            "macro_precision": precision_score(
                y_true, y_pred, average="macro", zero_division=0.0
            ),
            "macro_recall": recall_score(
                y_true, y_pred, average="macro", zero_division=0.0
            ),
            "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0.0),
        }


# endregion

# region wrappers to make the models work with TensorDicts


class MaskedLangModelInferenceWrapper(TensorDictModule[str, torch.Tensor]):  # type: ignore[misc]
    """A wrapper class for obtaining embeddings of a MaskedLanguageModel and
    TensorDicts.

    Args:
        model (MaskedLanguageModel): The masked language model to be used for inference.
        layers (list[str], optional): A list of layer names to be used from the model.
                                      Defaults to ["embedding", "encoder"].
    """

    def __init__(
        self,
        model: MaskedLanguageModel,
        layers: Sequence[str] = ("embedding", "encoder"),
    ) -> None:
        super().__init__(
            nn.Sequential(OrderedDict({layer: model[layer] for layer in layers})),
            in_keys={
                f: f
                for f in cast(MaskedLangModelEmbeddingLayer, model["embedding"]).features
                + [model.config["encoding"]]
            },
            out_keys=["output"],
        )
        self.encoding = model.config["encoding"]
        self.module.forward = self._star_forward

    @torch.no_grad()
    def _star_forward(self, **x: torch.Tensor) -> torch.Tensor:
        """This function is used to override the forward method of the
        nn.Sequential module to make it compatible with varying numbers of
        input arguments."""
        p = x.get(self.encoding)
        module = cast(nn.Sequential, self.module)
        output = cast(torch.Tensor, module[0](**x))
        for module_layer in module[1:]:
            output = cast(torch.Tensor, module_layer(output, p))
        return output


class MaskedLangModelEvalWrapper(TensorDictModule[str, torch.Tensor]):  # type: ignore[misc]
    """Wrapper class for evaluating the training of MaskedLanguageModel with
    TensorDicts.

    Args:
        model (MaskedLanguageModel): The masked language model to be evaluated.

    Attributes:
        model (MaskedLanguageModel): The masked language model being evaluated.
        true_target_keys (List[str]): The keys for the true target values.
        masked_out_keys (List[str]): The keys for the masked output values.

    Methods:
        forward(batch: TensorDict[str, torch.Tensor]) -> TensorDict[str, torch.Tensor]:
            Performs forward pass of the model on the given batch.
    """

    def __init__(self, model: MaskedLanguageModel) -> None:
        super().__init__(
            model,
            in_keys={
                f"{f}_mask": f
                for f in cast(MaskedLangModelEmbeddingLayer, model["embedding"]).features
            }
            | {model.config["encoding"]: model.config["encoding"]},
            out_keys=[
                f"{t}_pred"
                for t in cast(MultiClassificationHead, model["head"]).targets
            ],
            out_to_in_map=False,
        )
        self.true_target_keys = [
            f"{t}_true" for t in cast(MultiClassificationHead, model["head"]).targets
        ]
        self.masked_out_keys = [f"{k}_mask" for k in self.out_keys]

    def forward(
        self, batch: TensorDict[str, torch.Tensor]
    ) -> TensorDict[str, torch.Tensor]:
        mask_idx = torch.unbind(batch["mask_index"])
        batch = cast(TensorDict[str, torch.Tensor], super().forward(batch))
        model = cast(MaskedLanguageModel, self.module)
        head = cast(MultiClassificationHead, model["head"])
        for t, k in zip(head.targets, self.true_target_keys):
            batch[k] = head.vocabs[t].compute_targets(batch[t][mask_idx])
        for k, m in zip(self.out_keys, self.masked_out_keys):
            batch[m] = batch[k][mask_idx]
        return cast(TensorDict[str, torch.Tensor], batch)


class MaskedLangModelTrainWrapper(MaskedLangModelEvalWrapper):
    """Wrapper class for training MaskedLanguageModel with TensorDicts.

    Args:
        model (MaskedLanguageModel): The masked language model.
        loss_fn (MultiTargetLoss): The loss function.
    """

    def __init__(self, model: MaskedLanguageModel, loss_fn: MultiTargetLoss) -> None:
        super().__init__(model)
        self.loss_fn = loss_fn

    def forward(
        self, batch: TensorDict[str, torch.Tensor]
    ) -> TensorDict[str, torch.Tensor]:
        batch = super().forward(batch)
        batch["loss"] = self.loss_fn(
            tuple(batch[k] for k in self.masked_out_keys),
            tuple(batch[t] for t in self.true_target_keys),
        )
        return batch


# endregion

# region whole dataset clustering models


class AbstractDatasetGroupingModel:
    """An abstract base class for the aggregation of detectmate alerts.

    Methods:
        forward(data: AlertDataset) -> np.ndarray:
            If implemented, groups the dataset based on the underlying model.
    """

    def __call__(self, data: list[DetectorSchema]) -> np.ndarray:
        return self.forward(data)

    def forward(self, data: list[DetectorSchema]) -> np.ndarray:
        """If implemented, embeds the dataset based on its attributes."""
        raise NotImplementedError("forward method must be implemented in subclass!")


class TimeDelta(AbstractDatasetGroupingModel):
    """An alert grouping model that groups alerts based on the time differences
    between them as discussed in the paper [Dealing with Security Alert Flooding: Using Machine Learning
    for Domain-independent Alert Aggregation](https://dl.acm.org/doi/pdf/10.1145/3510581).
    A sequence of alerts is considered to be a group if the time difference between any two
    consecutive alerts is less than a specified delta.

    Args:
        delta (float): The time difference threshold for grouping. Defaults to 2.0.

    Methods:
        forward(data: list[DetectorSchema]) -> np.ndarray:
            Groups the dataset based on the time differences between alerts.
    """

    def __init__(
        self,
        config: AlertBERTAggregationConfig,
    ) -> None:
        self.config = config

    def forward(self, data: list[DetectorSchema]) -> np.ndarray:
        c = np.array([alert["extractedTimestamps"][-1] for alert in data])
        c = np.diff(c, prepend=c[0])
        c = np.where(c >= self.config.delta, 1, 0)
        return np.cumsum(c)


class AlertBERT(AbstractDatasetGroupingModel):
    """An alert grouping model that groups alerts based on embeddings obtained
    from masked language models. The model uses PCA for embedding
    dimensionality reduction and defines alert groups with a method that is
    equivalent to DBSCAN clustering with min_samples=1 and embedding distances
    defined by the time-cosine-metric.

    Args:
        model (MaskedLangModelInferenceWrapper): The masked language model to be used for alert embedding.
        config (AlertBERTAggregationConfig): Configuration of model parameters, for more information see
            the documentation of `detectmatelibrary.alert_aggrgation.AlertBertAggregationConfig`.
        dim_reduction (int, optional): The number of dimensions to reduce the embeddings to. Defaults to 2.
        delta (float, optional): The distance threshold for clustering. Defaults to 2.0.
        theta (float, optional): The scaling factor for the CombinedTimeCosineMetric. Defaults to 1.0.

    Methods:
        forward(data: AlertDataset) -> np.ndarray:
            Groups the dataset based on the embeddings obtained from the masked language model.
        time_cosine_metric(embeddings: np.ndarray, embeddings2: np.ndarray | None = None) -> np.ndarray:
            Computes the time-cosine-metric between two sets of embeddings.
    """

    def __init__(
        self,
        model: MaskedLanguageModel,
        config: AlertBERTAggregationConfig,
    ) -> None:
        super().__init__()
        self.config = config
        if not config.theta >= config.delta:
            raise ValueError(
                f"theta must be greater than or equal to delta ({self.config.theta} >= {self.config.delta}) \
                as it determines the maximal possoble value of the cosine distance!"
            )
        self.model = MaskedLangModelInferenceWrapper(model, layers=self.config.layers)
        self.collate_fn: Callable[[list[dict[str, list[Any]]]], Any] = BaseSequenceCollate(
            model.vocabs
        )
        self.dim_reduction = (
            PCA(n_components=self.config.dim_reduction)
            if self.config.dim_reduction
            else None
        )
        self.padding = 1024
        self.readout = 2048
        self.timedelta = TimeDelta(config)
        self.feature_extraction_fn: Callable[
            [list[DetectorSchema]], dict[str, list[Any]]
        ] = lambda x: AlertDataset(x).data

    def forward(self, data: list[DetectorSchema]) -> np.ndarray:
        # get embeddings of full dataset
        embeddings = self._get_embeddings(data)

        # compute pre clustering
        pre_clustering = self.timedelta(data)

        # this keeps track of how many alerts were in the previous pre-clusters
        alert_idx_offset = 0

        # iterate over all pre-clusters and perform agglomerative clustering
        pred = []
        next_label = 0

        for pre_cluster in range(pre_clustering[-1] + 1):
            current_alerts = pre_clustering == pre_cluster
            pre_cluster_size = np.sum(current_alerts)
            if pre_cluster_size == 1 or self.config.delta == self.config.theta:
                # either only one alert in the pre-cluster or all alerts belong to the same group,
                # so no need to compute distances
                alert_idx_offset += pre_cluster_size
                pred.append(next_label * np.ones(pre_cluster_size))
                next_label += 1
                continue
            pre_cluster_raw_time = np.array(
                [alert["extractedTimestamps"][-1] for alert in data]
            )[current_alerts]
            pre_cluster_time_length = pre_cluster_raw_time[-1] - pre_cluster_raw_time[0]

            if pre_cluster_time_length <= self.config.delta:
                # all alert pairs are relevant
                # we compute everything at once bc it is less complicated to implement
                distance_matrix = self.time_cosine_metric(
                    embeddings[alert_idx_offset: alert_idx_offset + pre_cluster_size]
                )
                pre_cluster_pred, n_labels = self._dist_matrix_to_connected_components(
                    distance_matrix, pre_cluster_size
                )
                pred.append(pre_cluster_pred + next_label)
                next_label += n_labels
                alert_idx_offset += pre_cluster_size
                continue

            # not all alert pairs are relevant,
            # we compute distance pairs in a (off-)diagonal-block-pattern covering the diagonals of
            # the distance matrix with rectangles of appropriate size for self.delta to save memory while
            # covering all relevant pairs.
            # for each block a preliminary clustering is computed, which produces in total 3 different
            # clusterings of the pre-cluster.
            # these 3 clusterings are then united to produce the final clustering

            next_prelim_label = 0
            primary_labels = []
            secondary_labels = []
            tertiary_labels = []

            # determine the block sizes
            square_sizes = []
            current_square_size = 1
            square_start_time = pre_cluster_raw_time[0]
            for i in range(1, pre_cluster_size):
                if pre_cluster_raw_time[i] - square_start_time < self.config.delta:
                    current_square_size += 1
                else:
                    square_sizes.append(current_square_size)
                    square_start_time = pre_cluster_raw_time[i]
                    current_square_size = 1
            square_sizes.append(current_square_size)
            square_sizes = np.array(square_sizes)
            if not square_sizes.sum() == pre_cluster_size:
                raise ValueError(
                    f"Sum of square sizes ({square_sizes.sum()}) does not match \
                        pre-cluster size ({pre_cluster_size})!"
                )

            # at first compute labels of the initial square
            distance_matrix = self.time_cosine_metric(
                embeddings[alert_idx_offset: alert_idx_offset + square_sizes[0]]
            )
            square_pred, n_labels = self._dist_matrix_to_connected_components(
                distance_matrix, square_sizes[0]
            )
            primary_labels.append(square_pred + next_prelim_label)
            next_prelim_label += n_labels

            # then compute the remaining distance pairs by first computing the off-diagonal rectangle
            # connecting the last square with the next one, and then the next diagonal square
            last_square_start = 0
            last_square_size = square_sizes[0]
            current_square_start = square_sizes[0]
            i = 1
            for current_square_size in square_sizes[1:]:
                # compute the distances between last and current square
                distances_current_to_last_square = self.time_cosine_metric(
                    embeddings[
                        alert_idx_offset + last_square_start: alert_idx_offset
                        + current_square_start
                    ],
                    embeddings[
                        alert_idx_offset + current_square_start: alert_idx_offset
                        + current_square_start
                        + current_square_size
                    ],
                )
                distances_current_to_last_square = (
                    distances_current_to_last_square < self.config.delta
                )

                matrix_idxs = np.nonzero(distances_current_to_last_square)
                square_pred, n_labels = self._get_connected_components(
                    matrix_idxs[0],
                    matrix_idxs[1] + last_square_size,  # change 1
                    current_square_size + last_square_size,
                )
                if i % 2:
                    secondary_labels.append(square_pred + next_prelim_label)
                else:
                    tertiary_labels.append(square_pred + next_prelim_label)
                next_prelim_label += n_labels

                # compute the distances of the current square
                distance_matrix = self.time_cosine_metric(
                    embeddings[
                        alert_idx_offset + current_square_start: alert_idx_offset
                        + current_square_start
                        + current_square_size
                    ]
                )
                square_pred, n_labels = self._dist_matrix_to_connected_components(
                    distance_matrix, current_square_size
                )
                primary_labels.append(square_pred + next_prelim_label)
                next_prelim_label += n_labels

                # update the start indices for the next square
                i += 1
                last_square_start = current_square_start
                last_square_size = current_square_size
                current_square_start += current_square_size

            # check and agglomerate the preliminary labels
            primary_labels = np.concatenate(primary_labels)
            secondary_labels = np.concatenate(secondary_labels)
            tertiary_labels = (
                np.concatenate(tertiary_labels)
                if len(tertiary_labels) > 0
                else np.array([])
            )
            if not len(primary_labels) == pre_cluster_size:
                raise ValueError(
                    f"Length of primary labels ({len(primary_labels)}) does not match \
                        pre-cluster size ({pre_cluster_size})!"
                )
            if not i % 2:
                if not len(secondary_labels) == pre_cluster_size:
                    raise ValueError(
                        f"Length of secondary labels ({len(secondary_labels)}) does not match \
                            pre-cluster size ({pre_cluster_size})!"
                    )
                if not (
                    len(tertiary_labels)
                    == pre_cluster_size - square_sizes[0] - square_sizes[-1]
                ):
                    raise ValueError(
                        f"Length of tertiary labels ({len(tertiary_labels)}) does not match \
                            pre-cluster size ({pre_cluster_size})!"
                    )
                tertiary_labels = np.concatenate(  # add additional labels to get sequences of same length
                    [
                        -1
                        * np.arange(
                            1, square_sizes[0] + 1
                        ),  # make sure the labels dont collide
                        tertiary_labels,
                        -1 * np.arange(1, square_sizes[-1] + 1)
                        - 2 * square_sizes[0],  # make sure the labels dont collide
                    ]
                )
            else:
                if not len(tertiary_labels) == pre_cluster_size - square_sizes[0]:
                    raise ValueError(
                        f"Length of tertiary labels ({len(tertiary_labels)}) does not match \
                            pre-cluster size ({pre_cluster_size})!"
                    )
                if not len(secondary_labels) == pre_cluster_size - square_sizes[-1]:
                    raise ValueError(
                        f"Length of secondary labels ({len(secondary_labels)}) does not match \
                            pre-cluster size ({pre_cluster_size})!"
                    )
                secondary_labels = np.concatenate(  # add additional labels to get sequences of same length
                    [
                        secondary_labels,
                        -1 * np.arange(1, square_sizes[-1] + 1),
                    ]  # make sure the labels dont collide
                )
                tertiary_labels = np.concatenate(  # add additional labels to get sequences of same length
                    [
                        -1 * np.arange(1, square_sizes[0] + 1)
                        - 2 * square_sizes[-1],  # make sure the labels dont collide
                        tertiary_labels,
                    ]
                )
            if not len(secondary_labels) == len(tertiary_labels):
                raise ValueError(
                    f"Length of secondary labels ({len(secondary_labels)}) does not match length of \
                        tertiary labels ({len(tertiary_labels)})!"
                )

            if len(tertiary_labels) > 0:
                secondary_labels, _ = self._unite_labels(
                    secondary_labels, tertiary_labels
                )
            primary_labels, n_labels = self._unite_labels(
                primary_labels,
                -1
                * (
                    1 + secondary_labels
                ),  # make sure the labels dont collide  # change 2
            )

            pred.append(primary_labels + next_label)
            next_label += n_labels
            alert_idx_offset += pre_cluster_size

        pred = np.concatenate(pred)
        if not alert_idx_offset == len(data):
            raise ValueError(
                f"Alert index offset ({alert_idx_offset}) does not match number of alerts ({len(data)})!"
            )
        if not len(pred) == len(data):
            raise ValueError(
                f"Length of predictions ({len(pred)}) does not match number of alerts ({len(data)})!"
            )
        if not np.max(pred) + 1 == next_label:
            raise ValueError(
                f"Max label ({np.max(pred)}) does not match next label ({next_label})!"
            )
        return pred

    def _dist_matrix_to_connected_components(
        self,
        distance_matrix: np.ndarray,
        n_alerts: int,
    ) -> tuple[np.ndarray, int]:
        """Converts a distance matrix to connected components.

        Args:
            distance_matrix (np.ndarray): The distance matrix to be converted.
            n_alerts (int): The number of alerts in the dataset.

        Returns:
            tuple[np.ndarray, int]: The connected components of the graph and the number
                of connected components found.
        """
        distance_matrix = distance_matrix < self.config.delta
        np.fill_diagonal(distance_matrix, False)
        matrix_idxs = np.nonzero(distance_matrix)
        return self._get_connected_components(matrix_idxs[0], matrix_idxs[1], n_alerts)

    def _get_connected_components(
        self,
        coords_0: np.ndarray,
        coords_1: np.ndarray,
        n_nodes: int,
    ) -> tuple[np.ndarray, int]:
        """Finds the connected components in the graph defined by the
        coordinates.

        Args:
            coords_0 (np.ndarray): The first set of coordinates.
            coords_1 (np.ndarray): The second set of coordinates.
            n_nodes (int): The number of nodes in the graph.

        Returns:
            np.ndarray: The connected components of the graph.
            int: The number of connected components.
        """
        # create adjacency matrix
        connections = np.ones_like(coords_0, dtype=bool)
        connections = coo_array(
            (
                connections,
                (coords_0, coords_1),
            ),
            shape=(n_nodes, n_nodes),
        )

        # find connected components aka groups
        connections = connections.tocsr()
        n_groups, pred = connected_components(connections, connection="strong")
        return pred, n_groups

    def _unite_labels(
        self, prelim_labels_1: np.ndarray[int], prelim_labels_2: np.ndarray[int]
    ) -> tuple[np.ndarray[int], int]:
        """Merges two clustering results into a single set of labels by merging
        all intersecting clusters.

        Args:
            prelim_labels_1 (np.ndarray[int]): The first set of preliminary labels.
            prelim_labels_2 (np.ndarray[int]): The second set of preliminary labels.

        Returns:
            np.ndarray[int]: The final set of labels after merging.
            int: The number of unique labels in the final set.
        """
        if not len(prelim_labels_1) == len(prelim_labels_2):
            raise ValueError(
                f"Length of preliminary labels 1 ({len(prelim_labels_1)}) does not match length of \
                    preliminary labels 2 ({len(prelim_labels_2)})!"
            )
        # check if the two sets of preliminary labels are disjoint
        if not set(prelim_labels_1).isdisjoint(set(prelim_labels_2)):
            raise ValueError(
                "Preliminary labels must be disjoint! "
                f"Found overlapping labels: {set(prelim_labels_1).intersection(set(prelim_labels_2))}"
            )

        # define maps to efficiently go back and forth between final and preliminary labels
        final_label_to_prelim_labels: list[set[int] | None] = []
        prelim_labels_to_final_label: dict[int, int] = {}

        for l1, l2 in zip(prelim_labels_1, prelim_labels_2):
            if (
                l1 in prelim_labels_to_final_label
                and l2 in prelim_labels_to_final_label
            ):
                # both preliminary labels are already assigned to final labels
                if prelim_labels_to_final_label[l1] == prelim_labels_to_final_label[l2]:
                    # the assigned final labels are the same, there is nothing to do
                    continue
                else:
                    # the assigned final labels are different.
                    # we merge them by transferring all preliminary labels of the second final label to the
                    # first one and then we mark the second final label as deleted
                    final_label = prelim_labels_to_final_label[l1]
                    old_l2_final_label = prelim_labels_to_final_label[l2]
                    final_labels = final_label_to_prelim_labels[final_label]
                    old_l2_labels = final_label_to_prelim_labels[old_l2_final_label]
                    if final_labels is None or old_l2_labels is None:
                        raise RuntimeError("Deleted label was referenced during clustering.")
                    final_labels.update(old_l2_labels)
                    for prelim_label in old_l2_labels:
                        prelim_labels_to_final_label[prelim_label] = final_label
                    final_label_to_prelim_labels[old_l2_final_label] = None

            elif l1 in prelim_labels_to_final_label:
                # only the first preliminary label is assigned to a final label
                # we assign the second preliminary label to the same final label
                final_label = prelim_labels_to_final_label[l1]
                labels = final_label_to_prelim_labels[final_label]
                if labels is None:
                    raise RuntimeError("Deleted label was referenced during clustering.")
                labels.add(l2)
                prelim_labels_to_final_label[l2] = final_label

            elif l2 in prelim_labels_to_final_label:
                # only the second preliminary label is assigned to a final label
                # we assign the first preliminary label to the same final label
                final_label = prelim_labels_to_final_label[l2]
                labels = final_label_to_prelim_labels[final_label]
                if labels is None:
                    raise RuntimeError("Deleted label was referenced during clustering.")
                labels.add(l1)
                prelim_labels_to_final_label[l1] = final_label

            else:
                # neither preliminary label is assigned to a final label
                # we create a new final label and assign both preliminary labels to it
                final_label = len(final_label_to_prelim_labels)
                final_label_to_prelim_labels.append(set((l1, l2)))
                prelim_labels_to_final_label[l1] = final_label
                prelim_labels_to_final_label[l2] = final_label

        # create the final label clustering and remove the gaps caused by deleted labels
        assigned_labels: list[int] = []
        for l1, l2 in zip(prelim_labels_1, prelim_labels_2):
            f1 = prelim_labels_to_final_label[l1]
            f2 = prelim_labels_to_final_label[l2]
            if not f1 == f2:
                raise ValueError(
                    f"Preliminary labels {l1} and {l2} are assigned to different final labels {f1} and {f2}!"
                )
            assigned_labels.append(f1)
        used_labels, final_labels = np.unique(
            np.array(assigned_labels), return_inverse=True
        )
        return final_labels, len(used_labels)

    def _get_embeddings(
        self,
        data: list[DetectorSchema],
        apply_dim_red: bool = True,
        add_time: bool = True,
    ) -> np.ndarray:
        if apply_dim_red and self.dim_reduction is None:
            raise ValueError(
                "Dimensionality reduction module must be specified if apply_dim_red is True!"
            )

        num_contexts = len(data) // self.readout
        remainder = len(data) % self.readout
        embeddings = []

        if remainder:
            batch_start = 0
            batch_end = min(len(data), remainder + self.padding)
            batch = self.feature_extraction_fn(data[batch_start:batch_end])
            batch = self.collate_fn([batch])
            batch = self.model(batch)
            embeddings.append(batch["output"][0, 0:remainder].cpu().numpy())

        for i in range(num_contexts):
            batch_start = max(0, i * self.readout + remainder - self.padding)
            batch_start_offset = min(self.padding, i * self.readout + remainder)
            batch_end = min(
                len(data), (i + 1) * self.readout + remainder + self.padding
            )
            batch_end_offset = min(
                self.padding, len(data) - (i + 1) * self.readout - remainder
            )
            batch = self.feature_extraction_fn(data[batch_start:batch_end])
            batch = self.collate_fn([batch])
            batch = self.model(batch)
            embeddings.append(
                batch["output"][
                    0, batch_start_offset: batch_end - batch_start - batch_end_offset
                ]
                .cpu()
                .numpy()
            )

        embeddings = np.concatenate(embeddings)
        if not embeddings.shape[0] == len(data):
            raise ValueError(
                "Number of embeddings does not match number of alerts! "
                f"Embeddings: {embeddings.shape[0]}, Alerts: {len(data)}"
            )

        # apply dimensionality reduction
        if apply_dim_red:
            dim_reduction = self.dim_reduction
            if dim_reduction is None:
                raise ValueError(
                    "Dimensionality reduction module must be specified if apply_dim_red is True!"
                )
            embeddings = dim_reduction.fit_transform(embeddings)

        # add time dimension
        if add_time:
            timestamps = np.array([alert["extractedTimestamps"][-1] for alert in data])
            embeddings = np.concatenate((embeddings, timestamps.reshape(-1, 1)), axis=1)

        return embeddings

    def time_cosine_metric(self, x: np.ndarray, y: np.ndarray = None) -> np.ndarray:
        if y is None:
            y = x
        if x.ndim == 1:
            x = x.unsequeze(0)
        if y.ndim == 1:
            y = y.unsequeze(0)
        return np.maximum(
            cosine_distances(x[:, :-1], y[:, :-1]) / 2.0 * self.config.theta,
            np.abs(x[:, -1][:, None] - y[:, -1]),
        )


# endregion
