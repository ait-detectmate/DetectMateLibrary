"""Helpers shared by the DeepLog and LogBERT model tests."""
import detectmatelibrary.utils.deep_learning._op as op
import detectmatelibrary.utils.deep_learning.logbert as logbert
import pytest
import jax.numpy as jnp
import jax
import sys
from typing import Any


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


def logbert_detection_draws(epochs: int) -> list[int]:
    """Detection mask draws for three windows after ``epochs`` epochs."""
    config = {
        "Model": {"hidden": 4, "n_layers": 1, "num_heads": 1, "dropout": 0.0, "max_len": 10},
        "Train": {"batch_size": 8, "learning_rate": 0.01, "epochs": epochs, "patience": 10},
    }
    model = logbert.LogBert(config=config)
    model.train(random_windows(60, 5), var_per=0.5)
    scorer, draws = model._scorer, []

    def spy(params: dict[str, Any], x: jnp.ndarray, i: int, top_k: int) -> jnp.ndarray:
        draws.append(int(i))
        return scorer(params, x, i, top_k)

    model._scorer = spy
    for seq in [(0, 1, 2, 3, 4), (1, 2, 3, 4, 5), (2, 3, 4, 5, 0)]:
        model.check_anomaly(seq, 1)
    return draws
